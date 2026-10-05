import sys
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mouse


def config():
    result = bytearray(63)
    result[:4] = bytes([0, 0x21, 0x31, 1])
    result[16:20] = bytes([6, 1, 8, 3])
    for index, dpi in enumerate([400, 800, 1600, 3200, 6400, 42000]):
        result[4 + index * 2:6 + index * 2] = dpi.to_bytes(2, 'little')
        result[51 + index * 2:53 + index * 2] = dpi.to_bytes(2, 'little')
    return bytes(result)


class MouseTests(unittest.TestCase):
    def test_config_matches_hardware_layout(self):
        result = mouse.decode_config(config())
        self.assertEqual((result['dpi'], result['stage'], result['pollingHz']), (800, 1, 2000))
        self.assertEqual(result['stages'], [400, 800, 1600, 3200, 6400, 42000])

    def test_invalid_config_never_becomes_editable(self):
        for body in (b'', bytes(63), bytes([0, 0, 0xff]) + config()[3:]):
            with self.assertRaises(ValueError):
                mouse.decode_config(body)

    def test_dpi_changes_only_current_axis_values(self):
        before = config()
        after = mouse.changed_config(before, dpi=1200)
        self.assertEqual(mouse.decode_config(after)['dpi'], 1200)
        self.assertEqual(mouse.decode_config(after)['dpiY'], 1200)
        self.assertTrue(all(before[i] == after[i] for i in range(63) if i not in (6, 7, 53, 54)))

    def test_stage_changes_only_wireless_index(self):
        before = config()
        after = mouse.changed_config(before, stage=2)
        self.assertEqual(after[2], 0x32)
        self.assertEqual(before[:2] + before[3:], after[:2] + after[3:])
        self.assertEqual(mouse.decode_config(after)['dpi'], 1600)

    def test_rejects_out_of_range_and_wrong_increment(self):
        for dpi in (0, 49, 123, 42050):
            with self.assertRaises(ValueError):
                mouse.changed_config(config(), dpi=dpi)
        with self.assertRaises(ValueError):
            mouse.changed_config(config(), stage=6)

    def test_confirmation_ignores_only_device_owned_bits(self):
        before = config()
        after = bytearray(before); after[3] = 2; after[17] |= 1
        self.assertTrue(mouse.matches_config(before, after))
        after[18] += 1
        self.assertFalse(mouse.matches_config(before, after))

    def test_apply_saves_backup_and_reads_back_before_success(self):
        before = config()
        after = mouse.changed_config(before, dpi=1200)
        identity = (0x3837).to_bytes(2, 'little') + bytes(6) + bytes([9, 91, 0])
        candidate = {'id': 'test', 'node': '/dev/test', 'canConfigure': True}
        with tempfile.TemporaryDirectory() as temp, patch.object(mouse, 'STATE', Path(temp)), patch.object(mouse, 'candidates', return_value=iter([candidate])), patch('builtins.open', mock_open()), patch.object(mouse, 'exchange', return_value=identity) as exchange, patch.object(mouse, 'read_config', side_effect=[before, before, after]), patch.object(mouse.time, 'sleep'):
            result = mouse.apply_setting('test', dpi=1200)
            self.assertEqual(result['dpi'], 1200)
            self.assertEqual(exchange.call_args.args[1:4], (0x12, 0x57, after))
            self.assertEqual(len(list(Path(temp).glob('mouse-before-*.json'))), 1)

    def test_failed_confirmation_is_not_reported_as_success(self):
        identity = (0x3837).to_bytes(2, 'little') + bytes(6) + bytes([9, 91, 0])
        with tempfile.TemporaryDirectory() as temp, patch.object(mouse, 'STATE', Path(temp)), patch.object(mouse, 'candidates', return_value=iter([{'id': 'test', 'node': '/dev/test', 'canConfigure': True}])), patch('builtins.open', mock_open()), patch.object(mouse, 'exchange', return_value=identity), patch.object(mouse, 'read_config', return_value=config()), patch.object(mouse.time, 'sleep'):
            with self.assertRaises(OSError):
                mouse.apply_setting('test', dpi=1200)

    def test_polling_write_preserves_wired_rate_and_other_config(self):
        before = config()
        after = bytearray(before); after[2] = 0x41
        identity = (0x3837).to_bytes(2, 'little') + bytes(6) + bytes([9, 91, 0])
        with tempfile.TemporaryDirectory() as temp, patch.object(mouse, 'STATE', Path(temp)), patch.object(mouse, 'candidates', return_value=iter([{'id': 'test', 'node': '/dev/test', 'canConfigure': True}])), patch('builtins.open', mock_open()), patch.object(mouse, 'exchange', return_value=identity) as exchange, patch.object(mouse, 'read_config', side_effect=[before, bytes(after)]), patch.object(mouse.time, 'sleep'):
            result = mouse.apply_setting('test', rate=4000)
            self.assertEqual(result['pollingHz'], 4000)
            self.assertEqual(exchange.call_args.args[1:4], (0x11, 0x41, bytes([2, 4])))

    def test_invalid_first_config_is_retried_without_profile_write(self):
        with patch.object(mouse, 'exchange', side_effect=[bytes(63), config()]) as exchange, patch.object(mouse.time, 'sleep'):
            self.assertEqual(mouse.read_config(None), config())
            self.assertTrue(all(call.args[1:] == (0x12, 0x67) for call in exchange.call_args_list))


if __name__ == '__main__':
    unittest.main()
