#!/usr/bin/env python3

import argparse
import datetime
import os
import sys
import yaml
from lib.krec import *


def get_header(header: Krec.Header):
    start_time = datetime.datetime.fromtimestamp(header.time)
    return {
        'client': header.app_name,
        'game name': header.game_name,
        'start time': f"{start_time} (local)",
        'player': f"{header.player_id} of {header.player_count}"
    }


def get_messages(playback: Krec.Playback, start_time: int):
    messages = []
    for id, event in enumerate(playback):
        if event.type == Krec.Playback.Event.chat:
            user = event.data.nickname
            time = datetime.datetime.fromtimestamp(start_time + (id/60))
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            messages.append(f"[{timestamp}] <{user}> {event.data.message}")
    return messages


def get_stats(playback: Krec.Playback):
    frames = [e for e in playback if e.type == Krec.Playback.Event.values]
    messages = [e for e in playback if e.type == Krec.Playback.Event.chat]
    return {
        'events': len(playback),
        'frames': len(frames),
        'seconds': round(len(frames)/60, 2),
        'messages': len(messages),
    }


def parse_arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument('file', nargs='+', help='krec recording (*.krec)')
    return parse.parse_args()


def main(args):
    for file in args.file:
        try:
            krec = Krec.from_file(file)
        except BaseException as e:
            print(f"Unable to open {file}: {e}")
            continue

        info = {
            'krec': {
                'name': os.path.basename(file),
                'header': get_header(krec.header),
                'stats': get_stats(krec.playback),
                'messages': get_messages(krec.playback, krec.header.time)
            }
        }

        yaml.dump(info, sys.stdout, sort_keys=False)
        print()


if __name__ == "__main__":
    args = parse_arguments()
    main(args)
