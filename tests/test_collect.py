import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location('collector', Path(__file__).resolve().parents[1] / 'collect.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def reply(percent=91, flags=9, vendor=0x3837, echo=6):
    data = bytearray(19)
    data[:2] = vendor.to_bytes(2, 'little')
    data[8:11] = bytes([flags, percent, 0])
    return bytes([0x11, echo ^ 255]) + bytes(x ^ 255 for x in data)


class BatteryTests(unittest.TestCase):
    def test_x9_requires_battery_field_and_valid_percentage(self):
        self.assertEqual(c.decode_x9_reply(bytes([0x55, 0x65, 90, 2])), 90)
        self.assertEqual(c.decode_x9_reply(bytes([0x55, 0x65, 0, 2])), 0)
        for data in (b'', bytes([0x55, 0x65, 90, 1]), bytes([0x55, 0x65, 255, 2]), bytes([0x41, 0x65, 90, 2])):
            self.assertIsNone(c.decode_x9_reply(data))

    def test_sleeping_mouse_preserves_settings_as_readonly(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(c, 'STATE', Path(temp)):
            row = dict(id='mouse', name='Mouse', kind='mouse', percent=91, connected=True, charging=False, settings={'dpi': 800})
            c.save([dict(row)], [])
            row['settings'], row['percent'], row['connected'] = None, None, None
            result = c.save([dict(row)], [])['devices'][0]
            self.assertEqual(result['settings']['dpi'], 800)
            self.assertFalse(result['settingsLive'])
            self.assertIsNotNone(result['settingsUpdatedAt'])

    def test_multiple_devices_keep_independent_alerts_and_settings(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(c, 'STATE', Path(temp)):
            first = dict(id='first', name='First', percent=91, connected=True, charging=False, settings={'dpi': 800})
            second = dict(id='second', name='Second', percent=None, connected=None, charging=False)
            c.save([dict(first), dict(second)], [])
            first['percent'], first['settings'] = None, None
            result = c.save([dict(first), dict(second)], [])
            saved = {d['id']: d for d in result['devices']}
            self.assertEqual(saved['first']['settings']['dpi'], 800)
            self.assertIsNone(saved['second']['settings'])
    def test_valid_wireless_identity(self):
        self.assertEqual(c.decode_mchose_reply(reply()), (91, True, False))

    def test_idle_receiver_does_not_claim_zero_battery(self):
        self.assertEqual(c.decode_mchose_reply(reply(0, flags=1)), (None, False, False))

    def test_empty_or_unrelated_reply_is_rejected(self):
        for value in (b'', bytes(21), reply(vendor=0), reply(echo=7)):
            self.assertIsNone(c.decode_mchose_reply(value))

    def test_invalid_percentage_does_not_enter_history(self):
        self.assertEqual(c.decode_mchose_reply(reply(255)), (None, True, False))
        self.assertEqual(c.battery_value(0), 0)

    def test_alerts_once_per_band_and_last_reading_survives_disconnect(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(c, 'STATE', Path(temp)), patch.object(c.subprocess, 'run') as notify:
            row = dict(id='test', name='Mouse', kind='mouse', source='USB', connected=True, percent=20, charging=False, detail='')
            c.save([dict(row)], [])
            c.save([dict(row)], [])
            self.assertEqual(notify.call_count, 1)
            row['percent'] = 10
            c.save([dict(row)], [])
            self.assertEqual(notify.call_count, 2)
            row['percent'], row['connected'] = None, False
            payload = c.save([dict(row)], [])
            self.assertIsNone(payload['devices'][0]['percent'])
            self.assertEqual(payload['devices'][0]['lastPercent'], 10)
            self.assertIsNotNone(payload['devices'][0]['lastSeen'])
            self.assertEqual(json.loads((Path(temp) / 'status.json').read_text()), payload)


if __name__ == '__main__':
    unittest.main()
