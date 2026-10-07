"""G515 fixed lighting through an isolated OpenRGB configuration."""
import json
import os
import select
import socket
import time
import re
import shutil
import subprocess
from pathlib import Path

STATE = Path.home() / '.local/state/omarchy-device-pulse'
CONFIG = Path.home() / '.config/OpenRGB/OpenRGB.json'
MODEL = 'G515 LS TKL'
PORT = 16743
SERVICE = 'omarchy-device-pulse-rgb.service'
ERROR = re.compile(r'^\s*Error:|cannot find device|not available for device|invalid mode|unknown mode|wrong number of colors', re.I | re.M)


def attach(rows):
    for row in rows:
        if row['kind'] == 'keyboard' and MODEL.lower() in row['name'].lower():
            row['lighting'] = dict(canEdit=row['connected'] is True and shutil.which('openrgb') is not None, color=load_color())


def apply_color(device_id, color, rows):
    row = next((r for r in rows if r['id'] == device_id), None)
    if not row or row['kind'] != 'keyboard' or MODEL.lower() not in row['name'].lower():
        raise ValueError('RGB disponível apenas para o Logitech G515 LS TKL.')
    if row['connected'] is not True:
        raise ValueError('Acorde o teclado e tente de novo.')
    if not re.fullmatch(r'[0-9a-fA-F]{6}', color):
        raise ValueError('Use uma cor com seis dígitos, como FF8500.')
    color = color.upper()
    isolated = prepare_config()
    host_mode()
    command = ['openrgb', '--config', str(isolated), '--noautoconnect', '--device', MODEL]
    if server_ready():
        command = ['openrgb', '--client', '127.0.0.1:' + str(PORT), '--noautoconnect', '--nodetect', '--device', MODEL]
    command += ['--mode', 'Off'] if color == '000000' else ['--mode', 'Static', '--color', color]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=35)
    except subprocess.TimeoutExpired:
        raise ValueError('O teclado demorou para responder. Acorde ele e tente de novo.')
    output = result.stdout + '\n' + result.stderr
    if result.returncode or ERROR.search(output):
        raise ValueError('Não consegui aplicar o RGB: ' + (output.strip() or 'OpenRGB falhou')[-350:])
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = STATE / 'lighting.tmp'
    temporary.write_text(json.dumps(dict(color=color)))
    temporary.replace(STATE / 'lighting.json')
    subprocess.run(['systemctl', '--user', 'start', SERVICE], capture_output=True, timeout=10)
    return 'Cor selecionada: ' + ('RGB apagado.' if color == '000000' else 'cor fixa #' + color + ' em todo o teclado.')


def server_ready():
    try:
        with socket.create_connection(('127.0.0.1', PORT), timeout=.2):
            return True
    except OSError:
        return False


def load_color():
    try:
        color = json.loads((STATE / 'lighting.json').read_text())['color']
        return color if isinstance(color, str) and re.fullmatch('[A-F0-9]{6}', color) else None
    except (OSError, ValueError, KeyError):
        return None


def prepare_config():
    try:
        detectors = json.loads(CONFIG.read_text())['Detectors']['detectors']
    except (OSError, ValueError, KeyError):
        raise ValueError('Abra o OpenRGB uma vez para preparar a configuração.')
    if not any('Logitech HID++ 2.0 G515 LS TKL' in key for key in detectors):
        raise ValueError('Esta versão do OpenRGB não suporta o G515.')
    isolated = STATE / 'openrgb-keyboard'
    isolated.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Disable every known detector except this model. Never scan the motherboard.
    (isolated / 'OpenRGB.json').write_text(json.dumps({'Detectors': {'detectors': {
        key: 'Logitech HID++ 2.0 G515 LS TKL' in key for key in detectors}},
        'LogitechHIDPP20IdleSettings': {'force_host_mode': True}}))
    return isolated


def device_node():
    for node in Path('/sys/class/hidraw').glob('*'):
        try:
            info = (node / 'device/uevent').read_text()
            if 'HID_ID=0003:0000046D:000040B4' in info and 'HID_NAME=Logitech G515 LS TKL' in info:
                return '/dev/' + node.name
        except OSError:
            pass
    return None


def host_mode():
    """Select volatile host mode via 8101. No profile/flash writes.
    Protocol: OpenRGB LogitechHIDPP20Controller::SetHostMode.
    """
    node = device_node()
    if node is None:
        raise OSError('Teclado indisponível. Acorde ele e atualize.')
    fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
    def request(feature, function, params):
        tag = function | 0x0b
        os.write(fd, bytes([0x11, 1, feature, tag]) + params.ljust(16, bytes(1)))
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if select.select([fd], [], [], max(0, deadline - time.monotonic()))[0]:
                reply = os.read(fd, 64)
                if len(reply) > 4 and reply[1] == 1:
                    if reply[2:4] == bytes([feature, tag]):
                        return reply[4:]
                    if reply[2] == 0xff and reply[3:5] == bytes([feature, tag]):
                        raise OSError('Teclado recusou o controle RGB.')
        raise OSError('Teclado sem resposta ao controle RGB.')
    try:
        feature = request(0, 0, bytes.fromhex('810100'))[0]
        if feature == 0:
            raise OSError('Controle de perfil G515 indisponível.')
        request(feature, 0x60, bytes([5]))
    finally:
        os.close(fd)


def serve():
    """Keep the isolated controller alive; it manages idle/wake and reconnects."""
    child = None
    try:
        while True:
            color = load_color()
            if color is None or device_node() is None:
                if child is not None:
                    child.terminate()
                    child.wait(timeout=10)
                    child = None
                time.sleep(2)
                continue
            if child is None or child.poll() is not None:
                try:
                    host_mode()
                    command = ['openrgb', '--config', str(prepare_config()), '--noautoconnect',
                               '--server', '--server-host', '127.0.0.1', '--server-port', str(PORT),
                               '--device', MODEL, '--mode', 'Off' if color == '000000' else 'Static']
                    if color != '000000':
                        command += ['--color', color]
                    child = subprocess.Popen(command)
                except (OSError, ValueError) as error:
                    print(str(error), flush=True)
            time.sleep(2)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(timeout=10)


if __name__ == '__main__':
    serve()
