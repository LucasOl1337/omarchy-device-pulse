"""MCHOSE receiver settings, using the documented M HUB feature protocol."""
import contextlib
import fcntl
import json
import time
from pathlib import Path

STATE = Path.home() / '.local/state/omarchy-device-pulse'
RATES = (125, 500, 1000, 2000, 4000, 8000)


@contextlib.contextmanager
def device_lock():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / 'devices.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def candidates():
    for sys in Path('/sys/class/hidraw').glob('*'):
        try:
            props = dict(line.split('=', 1) for line in (sys / 'device/uevent').read_text().splitlines() if '=' in line)
            descriptor = (sys / 'device/report_descriptor').read_bytes()
            if props.get('HID_ID') != '0003:00005253:00001020' or b'\x06\x01\xff' not in descriptor:
                continue
            name = props['HID_NAME'].replace('RealTek ', '').strip()
            yield dict(id='mchose:' + props.get('HID_UNIQ', '') + ':' + name, name=name, node='/dev/' + sys.name, canConfigure=name == 'MCHOSE K7 Ultra')
        except OSError:
            continue


def exchange(device, report, command, args=b'', read=True):
    size = 21 if report == 0x11 else 65
    if len(args) > size - 2:
        raise ValueError('Comando excede o tamanho do report')
    request = bytearray([report, command ^ 255] + [b ^ 255 for b in args] + [255] * (size - 2 - len(args)))
    for _ in range(3 if read else 1):
        fcntl.ioctl(device, 0xc0004806 | (size << 16), request)
        time.sleep(.06)
        if not read:
            return None
        reply = bytearray([report] + [0] * (size - 1))
        n = fcntl.ioctl(device, 0xc0004807 | (size << 16), reply)
        if n >= size and reply[0] == report and reply[1] ^ 255 == command and any(reply[2:]):
            return bytes(b ^ 255 for b in reply[2:])
        time.sleep(.12)
    raise OSError('Mouse sem resposta válida. Movimente o mouse e atualize.')


def decode_config(body):
    if len(body) != 63:
        raise ValueError('Configuração incompleta')
    count = body[16]
    stages = [int.from_bytes(body[4 + i * 2:6 + i * 2], 'little') for i in range(6)]
    stage, rate = body[2] & 15, body[2] >> 4
    if not 1 <= count <= 6 or stage >= count or rate >= len(RATES) or any(not 50 <= n <= 42000 or n % 50 for n in stages[:count]):
        raise ValueError('Configuração de DPI não reconhecida')
    y = int.from_bytes(body[51 + stage * 2:53 + stage * 2], 'little')
    return dict(dpi=stages[stage], dpiY=y, stage=stage, stages=stages[:count], pollingHz=RATES[rate], maxDpi=42000, minDpi=50, dpiStep=50)


def read_config(device):
    for attempt in range(3):
        body = exchange(device, 0x12, 0x67)
        try:
            decode_config(body)
            return body
        except ValueError:
            if attempt == 2:
                raise
            time.sleep(.14)


def read_settings(node):
    with open(node, 'r+b', buffering=0) as device:
        return decode_config(read_config(device))


def changed_config(before, dpi=None, stage=None):
    settings = decode_config(before)
    after = bytearray(before)
    if stage is not None:
        if not 0 <= stage < len(settings['stages']):
            raise ValueError('Etapa de DPI inválida')
        after[2] = (after[2] & 0xf0) | stage
    if dpi is not None:
        if not 50 <= dpi <= settings['maxDpi'] or dpi % 50:
            raise ValueError('DPI deve ser múltiplo de 50, entre 50 e ' + str(settings['maxDpi']))
        index = settings['stage']
        after[4 + index * 2:6 + index * 2] = dpi.to_bytes(2, 'little')
        after[51 + index * 2:53 + index * 2] = dpi.to_bytes(2, 'little')
    return bytes(after)


def matches_config(expected, actual):
    # The mouse owns reserved byte 3 and sensor bit 0.
    return len(actual) == len(expected) == 63 and all(a == b for i, (a, b) in enumerate(zip(expected, actual)) if i not in (3, 17)) and (expected[17] & 0xfe) == (actual[17] & 0xfe)


def apply_setting(device_id, dpi=None, stage=None, rate=None):
    if sum(v is not None for v in (dpi, stage, rate)) != 1:
        raise ValueError('Selecione uma configuração por vez')
    candidate = next((c for c in candidates() if c['id'] == device_id), None)
    if candidate is None:
        raise ValueError('Mouse compatível não encontrado')
    if not candidate.get('canConfigure'):
        raise ValueError('Edição de configurações ainda não validada pra este modelo')
    with open(candidate['node'], 'r+b', buffering=0) as device:
        identity = b''
        for _ in range(3):
            identity = exchange(device, 0x11, 6)
            if len(identity) >= 11 and int.from_bytes(identity[:2], 'little') in (0x3837, 0x5253):
                break
            time.sleep(.12)
        if len(identity) < 11 or int.from_bytes(identity[:2], 'little') not in (0x3837, 0x5253) or identity[8] & 7 != 1 or not identity[8] & 8:
            raise ValueError('Mouse não está conectado ao receptor')
        before = read_config(device)
        if rate is not None:
            if rate not in RATES:
                raise ValueError('Polling rate inválido')
            expected = bytearray(before)
            expected[2] = (RATES.index(rate) << 4) | (before[2] & 15)
        else:
            expected = changed_config(before, dpi, stage)
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = STATE / ('mouse-before-' + str(time.time_ns()) + '.json')
        backup.write_text(json.dumps(dict(device=device_id, body=before.hex(), savedAt=int(time.time()))))
        backup.chmod(0o600)
        if rate is not None:
            exchange(device, 0x11, 0x41, bytes([before[1] >> 4, RATES.index(rate)]), read=False)
        else:
            exchange(device, 0x12, 0x57, expected, read=False)
        for _ in range(5):
            time.sleep(.12)
            actual = read_config(device)
            if matches_config(expected, actual):
                return decode_config(actual)
        raise OSError('Mudança não confirmada pelo mouse. Atualize pra conferir.')
