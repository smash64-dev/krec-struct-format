#!/usr/bin/env python3

import argparse
from bizhawk import *
from lib.krec_pj64k import KrecPj64k as Krec
from lib.krec_pj64k import *


def determine_ports(values: list[tuple[int, Krec.Playback]]):
    plugged = [False, False, False, False]
    playback: Krec.Playback
    for _, playback in values:
        ports: list[Krec.Port] = playback.data.values.ports

        for port in ports:
            plugged[port.player_id-1] = True
    return plugged


def krec_mapping(bizhawk: BizHawk):
    mapping = bizhawk.default_input_log()
    input: Inputs
    map: Bk2Map
    for input in mapping.keys:
        if input:
            for map in input.maps:
                match map.bk2_key:
                    case 'Y Axis' | 'X Axis':
                        map.data_attr = 'stick_y' if map.y_axis else 'stick_x'

                    case 'A Up' | 'A Down' | 'A Left' | 'A Right':
                        map.data_attr = ''  # unused

                    case 'DPad U' | 'DPad D' | 'DPad L' | 'DPad R':
                        direction = map.bk2_key.split(' ')[1]
                        map.data_attr = f"{direction.lower()}_dpad"

                    case 'Start' | 'B' | 'A':
                        map.data_attr = f"{map.bk2_key.lower()}_button"

                    case 'Z' | 'L' | 'R':
                        map.data_attr = f"{map.bk2_key.lower()}_trig"

                    case 'C Up' | 'C Down' | 'C Left' | 'C Right':
                        direction = map.bk2_key.split(' ')[1][0]
                        map.data_attr = f"{direction.lower()}_cbutton"
    return mapping


def parse_arguments():
    parser = argparse.ArgumentParser(description=(
        'Converts a Kaillera recording (*.krec) to a Bizhawk TAS (*.bk2)'
    ))

    parser.add_argument('-k', metavar='KREC', required=True, dest='krec',
                        help='Kaillera recording file (*.krec)')
    parser.add_argument('-r', metavar='ROM', required=True, dest='rom',
                        help='ROM file used with the recording (*.z64)')
    parser.add_argument('-v', metavar='VERSION', required=False, dest='ver',
                        help='BizHawk emulator version (default: 2.8)')

    cores = parser.add_argument_group('cores')
    core = cores.add_mutually_exclusive_group()
    core_options = [c.value for c in BizHawk.Core]

    for value in core_options:
        core.add_argument(
            value[0], required=False, dest='core', action='store_const',
            help=f"Use {value[1]} Core", const=BizHawk.Core(value))

    parser.set_defaults(ver=2.8, core=BizHawk.Core.MUPEN64PLUS)
    return parser.parse_args()


def parse_inputs(values, input_log: InputLog, plugged: list[bool]):
    inputs = []
    playback: Krec.Playback
    for _, playback in values:
        data = [None] * 4
        ports: list[Krec.Port] = playback.data.values.ports
        port: Krec.Port

        for port in ports:
            if port.type == Krec.Port.Type.read_controller:
                data[port.player_id-1] = port.data.os_cont_pad

        inputs.append(input_log.__str__(data, sum(plugged)))
    return inputs


def parse_messages(messages):
    subtitles = []
    message: Krec.Playback
    for frame, message in messages:
        text = f"<{message.data.nickname}> {message.data.message}"
        subtitles.append(Subtitle(frame, text))

    return subtitles


def main(args):
    try:
        krec = Krec.from_file(args.krec)
        rom = Game(krec.header.game_name, args.rom)
    except Exception as e:
        print(e)
        exit(1)

    # after 100 frames we should have enough info
    chats = [(frame, event) for frame, event in enumerate(krec.playback)
             if event.type == Krec.Playback.Event.chat]
    values = [(frame, event) for frame, event in enumerate(krec.playback)
              if event.type == Krec.Playback.Event.values]
    ports = determine_ports(values[0:100])

    bizhawk = BizHawk(ver=args.ver, core=args.core, game=rom, ports=ports)
    inputs = parse_inputs(values, krec_mapping(bizhawk), ports)
    bizhawk.subtitles = parse_messages(chats)

    output = bizhawk.build_bk2(args.krec, inputs, f"{args.krec}.bk2")
    print(output)


if __name__ == "__main__":
    args = parse_arguments()
    main(args)
