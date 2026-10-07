import unittest
import ajazz


class AjazzTests(unittest.TestCase):
    def test_real_linux_reply_and_windows_prefix(self):
        self.assertEqual(ajazz.decode_battery(bytes.fromhex('00005a0100010200')), 90)
        self.assertEqual(ajazz.decode_battery(bytes.fromhex('0500006401010102')), 100)

    def test_no_link_garbage_and_out_of_range_are_unknown(self):
        for raw in ('0000000000000000', '05ad046401010102', '01005a0100010200', '0000ff0100010200', '00005a', '00005a0000000000'):
            self.assertIsNone(ajazz.decode_battery(bytes.fromhex(raw)))
