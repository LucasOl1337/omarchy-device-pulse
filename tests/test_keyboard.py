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
            with patch.object(keyboard, 'host_mode'), patch.object(keyboard, 'CONFIG', config), patch.object(keyboard, 'STATE', Path(folder)), patch.object(keyboard.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='Error: cannot find device', stderr='')):
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
            with patch.object(keyboard, 'STATE', state), patch.object(keyboard, 'prepare_config', return_value=state), patch.object(keyboard, 'host_mode'), patch.object(keyboard.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stdout='', stderr='USB unavailable')):
                with self.assertRaises(ValueError):
                    keyboard.apply_color('test-g515', 'FFFFFF', self.rows)
                self.assertEqual(keyboard.load_color(), 'C83200')

    def test_sleep_darkens_without_losing_the_selection_and_a_new_color_wakes(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            (state / 'lighting.json').write_text('{"color":"C83200"}')
            done = SimpleNamespace(returncode=0, stdout='', stderr='')
            with patch.object(keyboard, 'STATE', state), patch.object(keyboard, 'prepare_config', return_value=state), patch.object(keyboard, 'host_mode'), patch.object(keyboard.subprocess, 'run', return_value=done) as run:
                keyboard.set_sleep(True)
                self.assertEqual((keyboard.shown_color(), keyboard.load_color()), ('000000', 'C83200'))
                keyboard.set_sleep(False)
                self.assertEqual(keyboard.shown_color(), 'C83200')
                keyboard.set_sleep(True)
                keyboard.apply_color('test-g515', 'FF8500', self.rows)
                self.assertEqual(keyboard.shown_color(), 'FF8500')
                # Never through the SDK client: the keeper stops, the color goes direct, the keeper returns.
                calls = [call.args[0] for call in run.call_args_list[-3:]]
                self.assertEqual([c[:3] for c in (calls[0], calls[2])], [['systemctl', '--user', 'stop'], ['systemctl', '--user', 'start']])
                self.assertNotIn('--client', calls[1])

    def test_keeper_returns_even_when_the_keyboard_does_not_answer(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            with patch.object(keyboard, 'STATE', state), patch.object(keyboard, 'prepare_config', return_value=state), patch.object(keyboard, 'host_mode', side_effect=OSError('sem resposta')), patch.object(keyboard.subprocess, 'run') as run:
                with self.assertRaises(OSError):
                    keyboard.apply_color('test-g515', 'FF8500', self.rows)
                self.assertEqual(run.call_args_list[-1].args[0][:3], ['systemctl', '--user', 'start'])
                self.assertIsNone(keyboard.load_color())
