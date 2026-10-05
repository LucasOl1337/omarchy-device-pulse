#!/usr/bin/python3
"""Install DevicePulse as an Omarchy plugin and a user timer."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
PLUGIN = 'lucasol.device-pulse'
DEST = HOME / '.config/omarchy/plugins' / PLUGIN
UNITS = HOME / '.config/systemd/user'
STATE = HOME / '.local/state/omarchy-device-pulse'


def run(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True)


def deploy_ui(source, destination):
    """Give each QML generation a fresh URL in the running shell's cache."""
    files = sorted([*source.glob('*.qml'), *source.glob('*.js')])
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode() + b'\0' + path.read_bytes())
    generation = digest.hexdigest()[:20]
    runtime = destination / '.runtime' / generation
    runtime.parent.mkdir(parents=True, exist_ok=True)
    if not runtime.exists():
        temporary = Path(tempfile.mkdtemp(prefix='.staging-', dir=runtime.parent))
        try:
            for path in files:
                shutil.copy2(path, temporary / path.name)
            temporary.rename(runtime)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    manifest = json.loads((source / 'manifest.json').read_text())
    manifest['entryPoints']['barWidget'] = '.runtime/' + generation + '/Panel.qml'
    with tempfile.NamedTemporaryFile('w', prefix='.manifest-', dir=destination, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    try:
        temporary.chmod(0o644)
        temporary.replace(destination / 'manifest.json')
    finally:
        temporary.unlink(missing_ok=True)
    return generation


def install(udev=False):
    run('omarchy-plugin-validate', str(ROOT))
    # Preserve the initial local prototype's history and placement when upgrading.
    legacy = HOME / '.local/state/omarchy-trackers/peripherals'
    if legacy.exists():
        run('systemctl', '--user', 'disable', '--now', 'omarchy-peripherals.timer', check=False)
        run('systemctl', '--user', 'stop', 'omarchy-peripherals.service', check=False)
        if not STATE.exists():
            shutil.copytree(legacy, STATE)
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    DEST.mkdir(parents=True, exist_ok=True)
    for name in ('collect.py', 'mouse.py', 'control.py'):
        shutil.copy2(ROOT / name, DEST / name)
    deploy_ui(ROOT, DEST)
    UNITS.mkdir(parents=True, exist_ok=True)
    (UNITS / 'omarchy-device-pulse.service').write_text(
        '[Unit]\nDescription=DevicePulse peripheral battery tracker\n\n'
        '[Service]\nType=oneshot\nExecStart=/usr/bin/python3 ' + json.dumps(str(DEST / 'collect.py')) + '\n'
        'TimeoutStartSec=30\nUMask=0077\nNice=10\n')
    (UNITS / 'omarchy-device-pulse.timer').write_text(
        '[Unit]\nDescription=Refresh DevicePulse batteries every minute\n\n'
        '[Timer]\nOnStartupSec=15\nOnUnitInactiveSec=60\nAccuracySec=5\n\n'
        '[Install]\nWantedBy=timers.target\n')
    if udev:
        rule = ROOT / '70-device-pulse-mchose.rules'
        run('sudo', 'install', '-m', '644', str(rule), '/etc/udev/rules.d/70-device-pulse-mchose.rules')
        run('sudo', 'udevadm', 'control', '--reload-rules')
        for node in Path('/sys/class/hidraw').glob('*'):
            try:
                if any(identity in (node / 'device/uevent').read_text() for identity in ('HID_ID=0003:00005253:00001020', 'HID_ID=0003:00003837:00006045')):
                    run('sudo', 'udevadm', 'trigger', '--action=add', str(node))
            except OSError:
                pass
    config = HOME / '.config/omarchy/shell.json'
    if config.exists():
        data = json.loads(config.read_text())
        if any(w.get('id') == 'lol.peripherals' for section in data.get('bar', {}).get('layout', {}).values() for w in section):
            shutil.copy2(config, STATE / 'shell-before-upgrade.json')
            for section in data['bar']['layout'].values():
                for widget in section:
                    if widget.get('id') == 'lol.peripherals':
                        widget['id'] = PLUGIN
            config.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    run('systemctl', '--user', 'daemon-reload')
    run('systemctl', '--user', 'enable', '--now', 'omarchy-device-pulse.timer')
    run('systemctl', '--user', 'start', 'omarchy-device-pulse.service')
    run('omarchy-shell', 'shell', 'rescanPlugins')
    for _ in range(50):
        plugins = json.loads(run('omarchy-plugin-list', '--json').stdout)
        if any(p.get('id') == PLUGIN for p in plugins):
            break
        time.sleep(.1)
    plugins = json.loads(run('omarchy-plugin-list', '--json').stdout)
    if not any(p.get('id') == PLUGIN and p.get('enabled') for p in plugins):
        run('omarchy-plugin-enable', PLUGIN, '--after', 'omarchy.bluetooth')
    run('omarchy-shell', 'shell', 'reloadConfig')
    print('DevicePulse instalado. Clique no ícone de bateria ao lado do Bluetooth.')


def uninstall():
    run('omarchy-plugin-disable', PLUGIN, check=False)
    run('systemctl', '--user', 'disable', '--now', 'omarchy-device-pulse.timer', check=False)
    run('systemctl', '--user', 'stop', 'omarchy-device-pulse.service', check=False)
    for name in ('omarchy-device-pulse.timer', 'omarchy-device-pulse.service'):
        (UNITS / name).unlink(missing_ok=True)
    if DEST.exists():
        shutil.rmtree(DEST)
    run('systemctl', '--user', 'daemon-reload')
    run('omarchy-shell', 'shell', 'rescanPlugins')
    print('DevicePulse removido. Seu histórico continua em ' + str(STATE))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--udev', action='store_true', help='Install the optional MCHOSE receiver access rule (sudo)')
    parser.add_argument('--uninstall', action='store_true', help='Remove the plugin and timer; preserve history')
    args = parser.parse_args()
    if args.uninstall:
        uninstall()
    else:
        install(args.udev)
