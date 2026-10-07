import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import keyboard


class KeyboardTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(id='test-g515', name='Logitech G515 LS TKL', kind='keyboard', connected=True)]

    def test_openrgb_stdout_error_is_failure_even_with_exit_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'OpenRGB.json'
            config.write_text(json.dumps({'Detectors': {'detectors': {'Logitech HID++ 2.0 G515 LS TKL (wireless)': True, 'MSI': True}}}))
            with patch.object(keyboard, 'host_mode'), patch.object(keyboard, 'server_ready', return_value=False), patch.object(keyboard, 'CONFIG', config), patch.object(keyboard, 'STATE', Path(folder)), patch.object(keyboard.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='Error: cannot find device', stderr='')):
                with self.assertRaises(ValueError):
                    keyboard.apply_color('test-g515', 'FF8500', self.rows)
            isolated = json.loads((Path(folder) / 'openrgb-keyboard/OpenRGB.json').read_text())
            self.assertFalse(isolated['Detectors']['detectors']['MSI'])

    def test_wrong_device_disconnected_and_invalid_color_never_write(self):
        with patch.object(keyboard.subprocess, 'run') as run:
            for device, color in [('other', 'FF8500'), ('test-g515', 'invalid')]:
                with self.assertRaises(ValueError):
                    keyboard.apply_color(device, color, self.rows)
            self.rows[0]['connected'] = False
            with self.assertRaises(ValueError):
                keyboard.apply_color('test-g515', 'FF8500', self.rows)
            run.assert_not_called()

    def test_failed_command_preserves_previous_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            (state / 'lighting.json').write_text('{"color":"C83200"}')
            with patch.object(keyboard, 'STATE', state), patch.object(keyboard, 'prepare_config', return_value=state), patch.object(keyboard, 'host_mode'), patch.object(keyboard, 'server_ready', return_value=False), patch.object(keyboard.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stdout='', stderr='USB unavailable')):
                with self.assertRaises(ValueError):
                    keyboard.apply_color('test-g515', 'FFFFFF', self.rows)
                self.assertEqual(keyboard.load_color(), 'C83200')
