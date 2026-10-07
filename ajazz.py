"""AJAZZ 3151:5007 wireless battery, vendor F7 status query.
Reference: Aiacos/ajazz-control-center docs/protocols/mouse/aj_series_battery.md.
"""
import fcntl
import time
from pathlib import Path


def decode_battery(reply):
    offset = 3 if reply and reply[0] == 5 else 2
    if len(reply) < offset + 5:
        return None
    padding = reply[1:3] if offset == 3 else reply[:2]
    if any(padding):
        return None
    value = reply[offset]
    return value if 1 <= value <= 100 and any(reply[offset + 1:offset + 5]) else None


def battery(node):
    sys = Path('/sys/class/hidraw') / Path(node).name / 'device'
    if 'HID_ID=0003:00003151:00005007' not in (sys / 'uevent').read_text() or bytes.fromhex('06ffff0902') not in (sys / 'report_descriptor').read_bytes():
        raise OSError('Interface AJAZZ incorreta')
    with open(node, 'r+b', buffering=0) as device:
        for _ in range(3):
            query = bytearray(65)
            query[1] = 0xf7
            fcntl.ioctl(device, 0xc0414806, query)
            time.sleep(.06)
            reply = bytearray(65)
            reply[0] = 5
            count = fcntl.ioctl(device, 0xc0414807, reply)
            value = decode_battery(reply[:count])
            if value is not None:
                return value
            time.sleep(.15)
    raise OSError('AJAZZ sem telemetria de bateria')


def attach(rows):
    row = next((r for r in rows if r['id'] == 'usb:3151:5007'), None)
    if row is None:
        return
    for node in Path('/sys/class/hidraw').glob('*'):
        try:
            info = (node / 'device/uevent').read_text()
            desc = (node / 'device/report_descriptor').read_bytes()
            if 'HID_ID=0003:00003151:00005007' not in info or bytes.fromhex('06ffff0902') not in desc:
                continue
            try:
                row.update(percent=battery('/dev/' + node.name), connected=True, source='Receptor USB', detail='')
            except PermissionError:
                row['detail'] = 'Bateria sem acesso USB · instale a regra udev'
            except OSError:
                row['detail'] = 'Mouse dormindo ou sem resposta · última bateria abaixo'
        except OSError:
            continue
