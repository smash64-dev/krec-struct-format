meta:
  id: krec_pj64k
  title: Open Kaillera Recording from Project64K
  application: Project64KSE.exe
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
        enum: type
      - id: body
        type:
          switch-on: type
          cases:
            'type::get_keys': get_keys
            'type::read_controller': read_controller
            'type::apply_cheat': apply_cheat
    enums:
      type:
        32: get_keys
        33: read_controller
        36: apply_cheat
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

  apply_cheat:
    seq:
      - id: unknown1
        type: u2
      - id: cheat_id
        type: u4
      - id: code_id
        type: u4
      - id: command
        type: u4
      - id: value
        type: u4
      - id: unknown2
        size-eos: true
  get_keys:
    seq:
      - id: unknown1
        type: s2
      - id: raw_data
        type: u4
      - id: plugin
        type: u4
      - id: os_cont_pad
        type: os_cont_pad
      - id: unknown2
        size-eos: true
  os_cont_pad:
    seq:
      - id: button
        type: u2be
      - id: stick_x
        type: s1
      - id: stick_y
        type: s1
    instances:
      r_dpad:
        value: ((button >> 8) & 0b00000001) > 0
      l_dpad:
        value: ((button >> 8) & 0b00000010) > 0
      d_dpad:
        value: ((button >> 8) & 0b00000100) > 0
      u_dpad:
        value: ((button >> 8) & 0b00001000) > 0
      start_button:
        value: ((button >> 8) & 0b00010000) > 0
      z_trig:
        value: ((button >> 8) & 0b00100000) > 0
      b_button:
        value: ((button >> 8) & 0b01000000) > 0
      a_button:
        value: ((button >> 8) & 0b10000000) > 0
      r_cbutton:
        value: (button & 0b00000001) > 0
      l_cbutton:
        value: (button & 0b00000010) > 0
      d_cbutton:
        value: (button & 0b00000100) > 0
      u_cbutton:
        value: (button & 0b00001000) > 0
      r_trig:
        value: (button & 0b00010000) > 0
      l_trig:
        value: (button & 0b00100000) > 0
      reserved1:
        value: (button & 0b01000000) > 0
      reserved2:
        value: (button & 0b10000000) > 0
  pif_reserved:
    seq:
      - id: data
        size-eos: true
  read_controller:
    seq:
      - id: unknown1
        type: s2
      - id: pif_tx_len
        type: u1
      - id: pif_rx_len
        type: u1
      - id: pif_tx
        type: u1
        enum: pif_cmd
      - id: pif_rx
        size: pif_rx_len
        type:
          switch-on: pif_tx
          cases:
            'pif_cmd::read_values': os_cont_pad
            _: pif_reserved
      - id: unknown2
        size-eos: true
    enums:
      pif_cmd:
        0: get_status
        1: read_values
        2: read_pak
        3: write_pak
        4: read_eeprom
        5: write_eeprom
        255: reset_controller
    instances:
      os_cont_pad:
        value: pif_rx
        if: pif_tx == pif_cmd::read_values
