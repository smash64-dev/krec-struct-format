#!/usr/bin/env python3

import datetime
import os
import sys
from lib.krec import *


def show_header(header: Krec.Header):
    start_time = datetime.datetime.fromtimestamp(header.time)

    print("\nHeader:")
    print(f"  Client:\t{header.app_name}")
    print(f"  Game Name:\t{header.game_name}")
    print(f"  Start Time:\t{start_time} (local)")
    print(f"  Player:\t{header.player_id} of {header.player_count}")


def show_messages(playback: Krec.Playback, start_time: int):
    print("\nMessages:")

    for id, event in enumerate(playback):
        if event.type == Krec.Playback.Event.chat:
            text = event.data.message
            user = event.data.nickname
            time = datetime.datetime.fromtimestamp(start_time + (id/60))
            print(f"  [{time.strftime('%Y-%m-%d %H:%M:%S')}] <{user}> {text}")


def show_stats(playback: Krec.Playback):
    frames = [e for e in playback if e.type == Krec.Playback.Event.values]
    messages = [e for e in playback if e.type == Krec.Playback.Event.chat]

    print("\nStats:")
    print(f"  Events:\t{len(playback)}")
    print(f"  Frames:\t{len(frames)} (~{round(len(frames)/60, 2)} seconds)")
    print(f"  Messages:\t{len(messages)}")


try:
    if len(sys.argv) < 2:
        raise ValueError("Please specify a krec file")

    krec = Krec.from_file(sys.argv[1])
except Exception as e:
    print(e)
    print(f"Usage: {os.path.basename(__file__)} [*.krec]")
    exit(1)

show_header(krec.header)
show_stats(krec.playback)
show_messages(krec.playback, krec.header.time)
