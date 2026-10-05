import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('collector', Path(__file__).resolve().parents[1] / 'collect.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def reply(percent=91, flags=9, vendor=0x3837, echo=6):
    data = bytearray(19)
    data[:2] = vendor.to_bytes(2, 'little')
    data[8:11] = bytes([flags, percent, 0])
    return bytes([0x11, echo ^ 255]) + bytes(x ^ 255 for x in data)


class BatteryTests(unittest.TestCase):
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
