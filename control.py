#!/usr/bin/python3
"""Apply a single supported mouse setting and refresh DevicePulse."""
import argparse
import json
import os
import sys

import mouse
import collect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--dpi', type=int)
    action.add_argument('--stage', type=int)
    action.add_argument('--rate', type=int)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        with mouse.device_lock():
            settings = mouse.apply_setting(args.device, args.dpi, args.stage, args.rate)
            rows, errors = collect.collect()
            collect.save(rows, errors)
        print(json.dumps(dict(ok=True, message='Confirmado: ' + str(settings['dpi']) + ' DPI · ' + str(settings['pollingHz']) + ' Hz')))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps(dict(ok=False, message=str(error))))
        return 1


if __name__ == '__main__':
    sys.exit(main())
