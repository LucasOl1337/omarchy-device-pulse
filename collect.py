#!/usr/bin/python3
"""Read peripheral batteries and supported mouse settings."""
import fcntl
import json
import os
import sqlite3
import subprocess
import time
import argparse
import select
from contextlib import closing
from pathlib import Path

import dbus
import mouse

STATE = Path.home() / '.local/state/omarchy-device-pulse'


def battery_value(value):
    try:
        n = float(value)
        return round(n) if 0 <= n <= 100 else None
    except (TypeError, ValueError):
        return None


def decode_mchose_reply(reply):
    if len(reply) < 13 or reply[0] != 0x11 or reply[1] ^ 255 != 6:
        return None
    data = bytes(b ^ 255 for b in reply[2:])
    vendor = int.from_bytes(data[:2], 'little')
    if vendor not in (0x3837, 0x5253):
        return None
    connected = (data[8] & 7) != 1 or bool(data[8] & 8)
    return battery_value(data[9]) if connected else None, connected, data[10] == 1


def mchose_identity(node):
    # M HUB identity query, report 0x11 / command 0x06. No settings writes.
    # https://github.com/alexfrih/mchose-linux/blob/main/PROTOCOL.md
    with open(node, 'r+b', buffering=0) as device:
        for _ in range(3):
            request = bytearray([0x11, 0xf9] + [0xff] * 19)
            fcntl.ioctl(device, 0xc0154806, request)
            time.sleep(.05)
            reply = bytearray([0x11] + [0] * 20)
            fcntl.ioctl(device, 0xc0154807, reply)
            decoded = decode_mchose_reply(reply)
            if decoded is not None:
                return decoded
            time.sleep(.12)
    raise OSError('Dispositivo sem resposta')


def decode_x9_reply(reply):
    if len(reply) >= 4 and reply[:2] == b'\x55\x65' and reply[3] == 2:
        return battery_value(reply[2])
    return None


def x9_battery(node):
    # X9 3837:6045, status collection FF90, report 55, battery query 65/01.
    # Protocol reference: HeadsetControl/lib/devices/mchose_x9.hpp.
    descriptor = Path('/sys/class/hidraw', Path(node).name, 'device/report_descriptor').read_bytes()
    props = Path('/sys/class/hidraw', Path(node).name, 'device/uevent').read_text()
    if 'HID_ID=0003:00003837:00006045' not in props or b'\x06\x90\xff' not in descriptor or b'\x85\x55' not in descriptor:
        raise OSError('Interface de status X9 não encontrada')
    fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
    try:
        os.write(fd, bytes([0x55, 0x65, 1]) + bytes(61))
        deadline = time.monotonic() + .7
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], max(0, deadline - time.monotonic()))
            if not ready:
                break
            value = decode_x9_reply(os.read(fd, 64))
            if value is not None:
                return value
        raise OSError('X9 sem resposta de bateria')
    finally:
        os.close(fd)


def collect():
    rows, errors = [], []
    bus = dbus.SystemBus()
    try:
        service = bus.get_object('org.freedesktop.UPower', '/org/freedesktop/UPower')
        for path in service.EnumerateDevices(dbus_interface='org.freedesktop.UPower'):
            p = dict(bus.get_object('org.freedesktop.UPower', path).GetAll(
                'org.freedesktop.UPower.Device', dbus_interface='org.freedesktop.DBus.Properties'))
            if p.get('PowerSupply') or int(p.get('Type', 0)) not in (5, 6, 8, 9, 10, 11, 17, 18, 19):
                continue
            kind = {5: 'mouse', 6: 'keyboard', 17: 'headphones', 18: 'headphones', 19: 'headphones'}.get(int(p['Type']), 'device')
            present = bool(p.get('IsPresent'))
            percent = battery_value(p.get('Percentage')) if present else None
            # UPower calls BatteryLevel "unknown" even with a precise Percentage.
            if percent == 0 and int(p.get('State', 0)) == 0:
                percent = None
            rows.append(dict(id='upower:' + str(p.get('Serial') or p.get('NativePath') or path),
                name=str(p.get('Model') or 'Dispositivo sem fio'), kind=kind, source='UPower',
                connected=present, percent=percent, charging=int(p.get('State', 0)) == 1,
                detail='Bateria não informada' if present and percent is None else '', address=str(p.get('Serial', ''))))
    except dbus.DBusException:
        errors.append('UPower indisponível')
    try:
        objects = bus.get_object('org.bluez', '/').GetManagedObjects(dbus_interface='org.freedesktop.DBus.ObjectManager')
        for path, interfaces in objects.items():
            p = interfaces.get('org.bluez.Device1')
            if not p or not (p.get('Paired') or p.get('Connected')):
                continue
            address = str(p.get('Address', ''))
            duplicate = next((r for r in rows if r['address'].lower() == address.lower()), None)
            if duplicate:
                duplicate['connected'] = bool(p.get('Connected'))
                if not duplicate['connected']:
                    duplicate['percent'] = None
                continue
            icon = str(p.get('Icon', ''))
            kind = 'mouse' if 'mouse' in icon else 'keyboard' if 'keyboard' in icon else 'headphones' if 'audio' in icon else 'device'
            connected = bool(p.get('Connected'))
            battery = interfaces.get('org.bluez.Battery1', {})
            percent = battery_value(battery.get('Percentage')) if connected else None
            rows.append(dict(id='bluetooth:' + address, name=str(p.get('Alias') or p.get('Name') or address),
                address=address, kind=kind, source='Bluetooth', connected=connected,
                percent=percent, charging=False, detail='Bateria não informada' if connected and percent is None else ''))
    except dbus.DBusException:
        errors.append('Bluetooth indisponível')
    known_usb = {('3837', '6045'): ('MCHOSE X9', 'headphones'), ('3151', '5007'): ('AJAZZ 2.4G 8K', 'mouse')}
    for sys in Path('/sys/bus/usb/devices').glob('*'):
        try:
            key = ((sys / 'idVendor').read_text().strip(), (sys / 'idProduct').read_text().strip())
            if key in known_usb:
                name, kind = known_usb[key]
                rows.append(dict(id='usb:' + ':'.join(key), name=name, kind=kind, source='USB',
                    connected=None, percent=None, charging=False, detail='Receptor detectado · bateria não informada'))
        except OSError:
            continue
    # The headset status endpoint is separate from the mouse protocol.
    for sys in Path('/sys/class/hidraw').glob('*'):
        try:
            props = dict(line.split('=', 1) for line in (sys / 'device/uevent').read_text().splitlines() if '=' in line)
            if props.get('HID_ID') != '0003:00003837:00006045':
                continue
            row = next((r for r in rows if r['id'] == 'usb:3837:6045'), None)
            if row is None:
                continue
            try:
                row['percent'] = x9_battery('/dev/' + sys.name)
                row['connected'], row['source'], row['detail'] = True, 'Receptor USB', ''
            except PermissionError:
                row['detail'] = 'Leitura USB sem permissão'
            except OSError:
                row['detail'] = 'Receptor detectado · X9 sem leitura de bateria'
        except OSError:
            continue
    for candidate in mouse.candidates():
        row = dict(id=candidate['id'], name=candidate['name'], kind='mouse', source='Receptor USB',
            connected=None, percent=None, charging=False, detail='', settings=None, settingsError='')
        try:
            row['percent'], row['connected'], row['charging'] = mchose_identity(candidate['node'])
            if row['connected']:
                try:
                    row['settings'] = mouse.read_settings(candidate['node'])
                    row['settings']['canEdit'] = candidate['canConfigure']
                except (OSError, ValueError):
                    row['settingsError'] = 'DPI sem leitura nesta atualização'
        except PermissionError:
            row['detail'] = 'Leitura USB sem permissão'
        except OSError:
            row['detail'] = 'Sem resposta do mouse'
        rows.append(row)
    return rows, errors


def save(rows, errors):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    now = int(time.time())
    try:
        previous_devices = {r['id']: r for r in json.loads((STATE / 'status.json').read_text())['devices']}
    except (OSError, ValueError, KeyError):
        previous_devices = {}
    with closing(sqlite3.connect(STATE / 'history.sqlite')) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS samples (device TEXT, stamp INTEGER, percent INTEGER, charging INTEGER, PRIMARY KEY(device,stamp))')
        db.execute('CREATE TABLE IF NOT EXISTS alerts (device TEXT PRIMARY KEY, band INTEGER)')
        db.execute('DELETE FROM samples WHERE stamp < ?', (now - 30 * 86400,))
        for row in rows:
            row.setdefault('settings', None)
            row.setdefault('settingsError', '')
            row['settingsLive'] = row['settings'] is not None
            row['settingsUpdatedAt'] = now if row['settingsLive'] else previous_devices.get(row['id'], {}).get('settingsUpdatedAt')
            if not row['settingsLive']:
                row['settings'] = previous_devices.get(row['id'], {}).get('settings')
            percent = row['percent']
            if percent is not None:
                db.execute('INSERT OR REPLACE INTO samples VALUES (?,?,?,?)', (row['id'], now, percent, row['charging']))
                band = 2 if percent <= 10 else 1 if percent <= 20 else 0
                previous = db.execute('SELECT band FROM alerts WHERE device=?', (row['id'],)).fetchone()
                if band and not row['charging'] and band > (previous[0] if previous else 0):
                    try:
                        subprocess.run(['omarchy-notification-send', row['name'] + ': bateria baixa', f'{percent}% · Conecta pra carregar.'], capture_output=True, timeout=10)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                db.execute('INSERT OR REPLACE INTO alerts VALUES (?,?)', (row['id'], 0 if row['charging'] or percent > 25 else max(band, previous[0] if previous else 0)))
            samples = db.execute('SELECT stamp,percent FROM samples WHERE device=? AND stamp>=? ORDER BY stamp', (row['id'], now - 86400)).fetchall()
            row['history'] = [{'time': t, 'percent': p} for t, p in samples]
            last = db.execute('SELECT stamp,percent FROM samples WHERE device=? ORDER BY stamp DESC LIMIT 1', (row['id'],)).fetchone()
            row['lastSeen'] = last[0] if last else None
            row['lastPercent'] = last[1] if last else None
            row.pop('address', None)
    payload = dict(updatedAt=now, devices=sorted(rows, key=lambda r: (r['percent'] is None, r['percent'] if r['percent'] is not None else 101, r['name'])), errors=errors)
    temporary = STATE / 'status.tmp'
    temporary.write_text(json.dumps(payload, ensure_ascii=False))
    temporary.chmod(0o600)
    temporary.replace(STATE / 'status.json')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Read wireless device batteries for DevicePulse')
    parser.add_argument('--json', action='store_true', help='Also print the current snapshot')
    args = parser.parse_args()
    os.umask(0o077)
    with mouse.device_lock():
        rows, errors = collect()
        payload = save(rows, errors)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
