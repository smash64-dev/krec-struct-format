meta:
  id: krec
  title: Open Kaillera Recording file
  application: kailleraclient.dll
  file-extension: krec
  license: CC0-1.0
  endian: le
seq:
  - id: header
    type: header
  - id: playback
    type: playback
    repeat: eos
types:
  event_chat:
    seq:
      - id: nickname
        type: strz
        encoding: utf-8
      - id: message
        type: strz
        encoding: utf-8
  event_drop:
    seq:
      - id: nickname
        type: strz
        encoding: utf-8
      - id: player_id
        type: s4le
  event_values:
    seq:
      - id: size
        type: s2
      - id: values
        size: size
        type: values(_root.header.player_count, size)
  header:
    seq:
      - id: magic
        contents: 'KRC0'
      - id: app_name
        size: 128
        type: strz
        encoding: utf-8
      - id: game_name
        size: 128
        type: strz
        encoding: utf-8
      - id: time
        type: s4le
      - id: player_id
        type: s4le
      - id: player_count
        type: s4le
  playback:
    seq:
      - id: type
        type: s1
        enum: event
      - id: body
        type:
          switch-on: type
          cases:
            'event::chat': event_chat
            'event::values': event_values
            'event::drop': event_drop
    enums:
      event:
        8: chat
        18: values
        20: drop
  port:
    seq:
      - id: id
        type: s1
      - id: type
        type: s1
      - id: body
        size-eos: true
  values:
    params:
      - id: ports
        type: s2
      - id: total
        type: s2
    seq:
      - id: port
        size: total / ports
        type: port
        repeat: eos
