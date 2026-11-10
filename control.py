#!/usr/bin/python3
"""Apply a single supported peripheral setting and refresh DevicePulse."""
import argparse
import json
import os
import sys

import mouse
import collect
import keyboard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--dpi', type=int)
    action.add_argument('--stage', type=int)
    action.add_argument('--rate', type=int)
    action.add_argument('--color')
    action.add_argument('--sleep', choices=('on', 'off'), help='Keyboard dark for the night; off returns to the selected color')
    args = parser.parse_args()
    if args.sleep is None and not args.device:
        parser.error('--device is required')
    os.umask(0o077)
    try:
        if args.sleep is not None:
            print(json.dumps(dict(ok=True, message=keyboard.set_sleep(args.sleep == 'on'))))
            return 0
        with mouse.device_lock():
            if args.color is not None:
                rows, errors = collect.collect()
                message = keyboard.apply_color(args.device, args.color, rows)
                keyboard.attach(rows)
            else:
                settings = mouse.apply_setting(args.device, args.dpi, args.stage, args.rate)
                message = 'Confirmado: ' + str(settings['dpi']) + ' DPI · ' + str(settings['pollingHz']) + ' Hz'
                rows, errors = collect.collect()
            collect.save(rows, errors)
        print(json.dumps(dict(ok=True, message=message)))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps(dict(ok=False, message=str(error))))
        return 1


if __name__ == '__main__':
    sys.exit(main())
