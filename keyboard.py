"""G515 fixed lighting through an isolated OpenRGB configuration."""
import json
import re
import shutil
import subprocess
from pathlib import Path

STATE = Path.home() / '.local/state/omarchy-device-pulse'
CONFIG = Path.home() / '.config/OpenRGB/OpenRGB.json'
MODEL = 'G515 LS TKL'
ERROR = re.compile(r'^\s*Error:|cannot find device|not available for device|invalid mode|unknown mode|wrong number of colors', re.I | re.M)


def attach(rows):
    for row in rows:
        if row['kind'] == 'keyboard' and MODEL.lower() in row['name'].lower():
            row['lighting'] = dict(canEdit=row['connected'] is True and shutil.which('openrgb') is not None)


def apply_color(device_id, color, rows):
    row = next((r for r in rows if r['id'] == device_id), None)
    if not row or row['kind'] != 'keyboard' or MODEL.lower() not in row['name'].lower():
        raise ValueError('RGB disponível apenas para o Logitech G515 LS TKL.')
    if row['connected'] is not True:
        raise ValueError('Acorde o teclado e tente de novo.')
    if not re.fullmatch(r'[0-9a-fA-F]{6}', color):
        raise ValueError('Use uma cor com seis dígitos, como FF8500.')
    color = color.upper()
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
        key: 'Logitech HID++ 2.0 G515 LS TKL' in key for key in detectors}}}))
    command = ['openrgb', '--config', str(isolated), '--noautoconnect', '--device', MODEL]
    command += ['--mode', 'Off'] if color == '000000' else ['--mode', 'Static', '--color', color]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=35)
    except subprocess.TimeoutExpired:
        raise ValueError('O teclado demorou para responder. Acorde ele e tente de novo.')
    output = result.stdout + '\n' + result.stderr
    if result.returncode or ERROR.search(output):
        raise ValueError('Não consegui aplicar o RGB: ' + (output.strip() or 'OpenRGB falhou')[-350:])
    return 'Comando enviado: ' + ('RGB apagado.' if color == '000000' else 'cor fixa #' + color + ' em todo o teclado.')
