meta:
  id: krec_generic
  title: Open Kaillera Recording file
  application: kailleraclient.dll
  file-extension: krec
  license: CC0-1.0
seq:
  - id: header
    type: header
  - id: playback
    type: playback
    repeat: eos
types:
  empty: {}
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
        type: s2le
      - id: values
        size: size
        type:
          switch-on: size
          cases:
            0: empty
            _: values
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
    seq:
      - id: port
        size: 24
        type: port
        repeat: eos
