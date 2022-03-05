#!/usr/bin/env python3

import json
import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from enum import Enum
from typing import Callable


@dataclass
class Bk2Map:
    bk2_key: str
    bk2_value: str
    data_attr: str = ''
    x_axis: bool = False
    y_axis: bool = False

    def swap_axis(self, swap: bool):
        obj = self
        if swap and self.x_axis:
            obj.bk2_key = self.bk2_key.replace('X', 'Y')
            obj.data_attr = obj.data_attr.replace('X', 'Y').replace('x', 'y')
        if swap and self.y_axis:
            obj.bk2_key = self.bk2_key.replace('Y', 'X')
            obj.data_attr = obj.data_attr.replace('Y', 'X').replace('y', 'x')
        return obj


@dataclass
class Comment:
    message: str

    def __str__(self):
        return f"{self.message}\r\n"


@dataclass
class Game:
    name: str
    rom_path: str

    def sha1(self):
        return hashlib.sha1(open(self.rom_path, 'rb').read()).hexdigest()


@dataclass
class Header:
    emu_version: float
    game_name: str
    sha1: str
    core: str
    movie_version: float = 2.0
    author: str = "default user"
    platform: str = "N64"
    board: str = 'unknown'

    def __str__(self):
        return (
            f"MovieVersion BizHawk v{self.movie_version}\r\n"
            f"Author {self.author}\r\n"
            f"emuVersion Version {self.emu_version}\r\n"
            f"OriginalEmuVersion Version {self.emu_version}\r\n"
            f"Platform {self.platform}\r\n"
            f"GameName {self.game_name}\r\n"
            f"SHA1 {self.sha1.upper()}\r\n"
            f"Core {self.core}\r\n"
            f"BoardName {self.board}\r\n"
            f"rerecordCount 1\r\n"
        )


@dataclass
class Inputs:
    maps: list[Bk2Map]
    empty: str = '.'

    def __str__(self, data=None, swap: bool = False):
        output = ''
        for map in self.maps:
            if map.x_axis or map.y_axis:
                if data and map.data_attr:
                    swapped = map.swap_axis(swap)
                    prop = getattr(data, swapped.data_attr)
                    output += str(prop).rjust(5) + ','
                else:
                    output += str(0).rjust(5) + ','
            else:
                if data and map.data_attr:
                    prop = getattr(data, map.data_attr)
                    output += map.bk2_value if prop else self.empty
                else:
                    output += self.empty
        return output


@dataclass
class InputLog:
    power: Inputs
    keys: list[Inputs]
    port_swap: list[bool]
    tag: str = 'Input'

    def footer(self):
        return f"[/{self.tag}]\r\n"

    def header(self):
        return f"[{self.tag}]\r\n"

    def log_key(self, players: int = 4):
        log_key = 'log_key:#'
        for map in self.power.maps:
            log_key += f"{map.bk2_key}|"

        for id, keys in zip(range(players), self.keys):
            log_key += '#'
            for map in keys.maps:
                swap = map.swap_axis(self.port_swap[id])
                log_key += f"P{id+1} {swap.bk2_key}|"
        return f"{log_key}\r\n"

    def __str__(self, inputs: list, players: int = 4):
        output = '|'
        output += f"{str(self.power)}|"

        for id, input in zip(range(players), inputs):
            keys = self.keys[id]
            port_swap = self.port_swap[id]
            output += f"{keys.__str__(input, port_swap)}|"
        return f"{output}\r\n"


@dataclass
class Subtitle:
    frame: int
    message: str
    x_pos: int = 0              # (0, 0) is top left corner
    y_pos: int = 0              # (0, 0) is top left corner
    length: int = 60            # # of frames to display
    color: str = 'FFFFFFFF'     # ARGB

    def __str__(self):
        return (
            f"subtitle {self.frame} {self.x_pos} {self.y_pos} "
            f"{self.length} {self.message}\r\n"
        )


@dataclass
class SyncSettings:
    type: str
    ports: list[int]
    set_controllers: Callable[[dict, list[int]], dict]
    sync_settings: dict

    def build_settings(self):
        full_type = (
            f"BizHawk.Emulation.Cores.Consoles.Nintendo.{self.type}, "
            "BizHawk.Emulation.Cores"
        )
        settings = {'o': {"$type": full_type}}
        settings.update(self.sync_settings)
        return self.set_controllers(settings, self.ports)

    def to_json(self):
        return json.dumps(
            self.build_settings(), separators=(',', ':')) + "\r\n"


class BizHawk(object):
    # supported cores
    class Core(Enum):
        ARES_ACCURACY = ('-a', 'Ares64 (Accuracy)')
        ARES_PERFORMANCE = ('-p', 'Ares64 (Performance)')
        MUPEN64PLUS = ('-m', 'Mupen64Plus')

    def __init__(self, ver: float, core: Core, game: Game, ports: list[bool]):
        self.game = game
        self.ports = ports
        self.players = sum(ports)

        self.comments: list[Comment] = []
        self.header = Header(ver, game.name, game.sha1(), core.value[1])
        self.input_log: InputLog = self.default_input_log()
        self.subtitles: list[Subtitle] = []

        match core:
            case self.Core.ARES_ACCURACY:
                self.sync_settings = SyncSettings(
                    type='Ares64.Accuracy.Ares64+Ares64SyncSettings',
                    ports=self.ports,
                    set_controllers=self.__ares_set_controllers,
                    sync_settings=self.__ares_sync_settings())

            case self.Core.ARES_PERFORMANCE:
                self.sync_settings = SyncSettings(
                    type='Ares64.Performance.Ares64+Ares64SyncSettings',
                    ports=self.ports,
                    set_controllers=self.__ares_set_controllers,
                    sync_settings=self.__ares_sync_settings())

            case self.Core.MUPEN64PLUS:
                self.sync_settings = SyncSettings(
                    type='N64.N64sync_settings',
                    ports=self.ports,
                    set_controllers=self.__mupen64plus_set_controllers,
                    sync_settings=self.__mupen64plus_sync_settings())

            case _:
                raise ValueError('Supplied core is not supported')

    def build_bk2(self, original: str, inputs: list, output: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            _, ext = os.path.splitext(original)
            shutil.copy(original, f"{tmpdir}/original{ext}")

            with open(f"{tmpdir}/Comments.txt", 'w') as comments:
                for comment in self.comments:
                    comments.write(str(comment))

            open(f"{tmpdir}/Header.txt", 'w').write(str(self.header))

            with open(f"{tmpdir}/Input Log.txt", 'w') as input_log:
                input_log.write(self.input_log.header())
                input_log.write(self.input_log.log_key(self.players))
                for input in inputs:
                    input_log.write(input)
                input_log.write(self.input_log.footer())

            with open(f"{tmpdir}/Subtitles.txt", 'w') as subtitles:
                for subtitle in self.subtitles:
                    subtitles.write(str(subtitle))

            with open(f"{tmpdir}/SyncSettings.json", 'w') as sync_settings:
                sync_settings.write(self.sync_settings.to_json())

            archive = shutil.make_archive(output, 'zip', tmpdir)
            name, ext = os.path.splitext(archive)
            os.rename(archive, name)
        return name

    # input log - order matters here
    def default_input_log(self):
        power_maps = [Bk2Map('Reset', ''), Bk2Map('Power', '')]
        key_maps = [
            Bk2Map('Y Axis',  '', y_axis=True),
            Bk2Map('X Axis',  '', x_axis=True),
            # TODO: these are not used by Ares
            Bk2Map('A Up',    ''),
            Bk2Map('A Down',  ''),
            Bk2Map('A Left',  ''),
            Bk2Map('A Right', ''),
            Bk2Map('DPad U',  'U'),
            Bk2Map('DPad D',  'D'),
            Bk2Map('DPad L',  'L'),
            Bk2Map('DPad R',  'R'),
            Bk2Map('Start',   'S'),
            Bk2Map('Z',       'Z'),
            Bk2Map('B',       'B'),
            Bk2Map('A',       'A'),
            Bk2Map('C Up',    'u'),
            Bk2Map('C Down',  'd'),
            Bk2Map('C Left',  'l'),
            Bk2Map('C Right', 'r'),
            Bk2Map('L',       'l'),
            Bk2Map('R',       'r'),
        ]
        port_swaps = [False, True, False, True]

        port_maps = [None, None, None, None]
        for id, plugged in enumerate(self.ports):
            port_maps[id] = Inputs(key_maps) if plugged else None
        return InputLog(Inputs(power_maps), port_maps, port_swaps)

    # ares cores
    def __ares_set_controllers(self, settings, ports):
        for id, port in enumerate(ports):
            settings["o"][f"P{id+1}Controller"] = 2 if port else 0
        return settings

    def __ares_sync_settings(self):
        return {
            # "EnableVulkan": True,
            "RestrictAnalogRange": False,
            # "SuperSample": False,
            # "VulkanUpscale": 1
        }

    # mupen64plus core
    def __mupen64plus_set_controllers(self, settings, ports):
        controllers = [None] * 4
        for id, port in enumerate(ports):
            controllers[id] = {"PakType": 1, "IsConnected": bool(port)}

        settings["o"]["Controllers"] = controllers
        return settings

    def __mupen64plus_sync_settings(self):
        return {
            "Core": 1,
            "Rsp": 0,
            "VideoPlugin": 4,
            "DisableExpansionSlot": True,
            "RicePlugin": {
                "FrameBufferSetting": 0,
                "FrameBufferWriteBackControl": 0,
                "RenderToTexture": 0,
                "ScreenUpdateSetting": 4,
                "Mipmapping": 2,
                "FogMethod": 0,
                "ForceTextureFilter": 0,
                "TextureEnhancement": 0,
                "TextureEnhancementControl": 0,
                "TextureQuality": 0,
                "OpenGLDepthBufferSetting": 16,
                "MultiSampling": 0,
                "ColorQuality": 0,
                "OpenGLRenderSetting": 0,
                "AnisotropicFiltering": 0,
                "NormalAlphaBlender": False,
                "FastTextureLoading": False,
                "AccurateTextureMapping": True,
                "InN64Resolution": False,
                "SaveVRAM": False,
                "DoubleSizeForSmallTxtrBuf": False,
                "DefaultCombinerDisable": False,
                "EnableHacks": True,
                "WinFrameMode": False,
                "FullTMEMEmulation": False,
                "OpenGLVertexClipper": False,
                "EnableSSE": True,
                "EnableVertexShader": False,
                "SkipFrame": False,
                "TexRectOnly": False,
                "SmallTextureOnly": False,
                "LoadHiResCRCOnly": True,
                "LoadHiResTextures": False,
                "DumpTexturesToFiles": False,
                "UseDefaultHacks": True,
                "DisableTextureCRC": False,
                "DisableCulling": False,
                "IncTexRectEdge": False,
                "ZHack": False,
                "TextureScaleHack": False,
                "PrimaryDepthHack": False,
                "Texture1Hack": False,
                "FastLoadTile": False,
                "UseSmallerTexture": False,
                "VIWidth": -1,
                "VIHeight": -1,
                "UseCIWidthAndRatio": 0,
                "FullTMEM": 0,
                "TxtSizeMethod2": False,
                "EnableTxtLOD": False,
                "FastTextureCRC": 0,
                "EmulateClear": False,
                "ForceScreenClear": False,
                "AccurateTextureMappingHack": 0,
                "NormalBlender": 0,
                "DisableBlender": False,
                "ForceDepthBuffer": False,
                "DisableObjBG": False,
                "FrameBufferOption": 0,
                "RenderToTextureOption": 0,
                "ScreenUpdateSettingHack": 0,
                "EnableHacksForGame": 0
            },
            "GlidePlugin": {
                "wfmode": 1,
                "wireframe": False,
                "card_id": 0,
                "flame_corona": False,
                "ucode": 2,
                "autodetect_ucode": True,
                "motionblur": False,
                "fb_read_always": False,
                "unk_as_red": False,
                "filter_cache": False,
                "fast_crc": False,
                "disable_auxbuf": False,
                "fbo": False,
                "noglsl": True,
                "noditheredalpha": True,
                "tex_filter": 0,
                "fb_render": False,
                "wrap_big_tex": False,
                "use_sts1_only": False,
                "soft_depth_compare": False,
                "PPL": False,
                "fb_optimize_write": False,
                "fb_optimize_texrect": True,
                "increase_texrect_edge": False,
                "increase_primdepth": False,
                "fb_ignore_previous": False,
                "fb_ignore_aux_copy": False,
                "fb_hires_buf_clear": True,
                "force_microcheck": False,
                "force_depth_compare": False,
                "fog": True,
                "fillcolor_fix": False,
                "fb_smart": False,
                "fb_read_alpha": False,
                "fb_get_info": False,
                "fb_hires": True,
                "fb_clear": False,
                "detect_cpu_write": False,
                "decrease_fillrect_edge": False,
                "buff_clear": True,
                "alt_tex_size": False,
                "UseDefaultHacks": True,
                "enable_hacks_for_game": 0,
                "swapmode": 1,
                "stipple_pattern": 1041204192,
                "stipple_mode": 2,
                "scale_y": 100000,
                "scale_x": 100000,
                "offset_y": 0,
                "offset_x": 0,
                "lodmode": 0,
                "fix_tex_coord": 0,
                "filtering": 1,
                "depth_bias": 20
            },
            "Glide64mk2Plugin": {
                "wrpFBO": True,
                "card_id": 0,
                "use_sts1_only": False,
                "optimize_texrect": True,
                "increase_texrect_edge": False,
                "ignore_aux_copy": False,
                "hires_buf_clear": True,
                "force_microcheck": False,
                "fog": True,
                "fb_smart": False,
                "fb_read_alpha": False,
                "fb_hires": True,
                "detect_cpu_write": False,
                "decrease_fillrect_edge": False,
                "buff_clear": True,
                "alt_tex_size": False,
                "swapmode": 1,
                "stipple_pattern": 1041204192,
                "stipple_mode": 2,
                "lodmode": 0,
                "filtering": 0,
                "wrpAnisotropic": False,
                "correct_viewport": False,
                "force_calc_sphere": False,
                "pal230": False,
                "texture_correction": True,
                "n64_z_scale": False,
                "old_style_adither": False,
                "zmode_compare_less": False,
                "adjust_aspect": True,
                "clip_zmax": True,
                "clip_zmin": False,
                "force_quad3d": False,
                "useless_is_useless": False,
                "fb_read_always": False,
                "fb_get_info": False,
                "fb_render": True,
                "aspectmode": 0,
                "fb_crc_mode": 1,
                "fast_crc": True,
                "UseDefaultHacks": True,
                "enable_hacks_for_game": 0,
                "read_back_to_screen": 0
            },
            "GLideN64Plugin": {
                "BackgroundsMode": 1,
                "UseDefaultHacks": True,
                "MultiSampling": 0,
                "AspectRatio": 1,
                "BufferSwapMode": 0,
                "UseNativeResolutionFactor": 0,
                "bilinearMode": 0,
                "enableHalosRemoval": False,
                "MaxAnisotropy": False,
                "CacheSize": 8000,
                "ShowInternalResolution": False,
                "ShowRenderingResolution": False,
                "FXAA": False,
                "EnableNoise": True,
                "EnableLOD": True,
                "EnableHWLighting": False,
                "EnableShadersStorage": True,
                "CorrectTexrectCoords": 0,
                "EnableNativeResTexrects": False,
                "EnableLegacyBlending": False,
                "EnableFragmentDepthWrite": True,
                "EnableFBEmulation": True,
                "EnableCopyAuxiliaryToRDRAM": False,
                "EnableN64DepthCompare": True,
                "EnableOverscan": False,
                "OverscanNtscTop": 0,
                "OverscanNtscBottom": 0,
                "OverscanNtscLeft": 0,
                "OverscanNtscRight": 0,
                "OverscanPalTop": 0,
                "OverscanPalBottom": 0,
                "OverscanPalLeft": 0,
                "OverscanPalRight": 0,
                "DisableFBInfo": True,
                "FBInfoReadColorChunk": False,
                "FBInfoReadDepthChunk": True,
                "EnableCopyColorToRDRAM": 1,
                "EnableCopyDepthToRDRAM": 2,
                "EnableCopyColorFromRDRAM": False,
                "txFilterMode": 0,
                "txEnhancementMode": 0,
                "txDeposterize": False,
                "txFilterIgnoreBG": False,
                "txCacheSize": 100,
                "txHiresEnable": False,
                "txHiresFullAlphaChannel": False,
                "txEnhancedTextureFileStorage": False,
                "txHiresTextureFileStorage": False,
                "txHresAltCRC": False,
                "txDump": False,
                "txCacheCompression": True,
                "txForce16bpp": False,
                "txSaveCache": True,
                "txPath": "",
                "EnableBloom": False,
                "bloomThresholdLevel": 4,
                "bloomBlendMode": 0,
                "blurAmount": 10,
                "blurStrength": 20,
                "ForceGammaCorrection": False,
                "GammaCorrectionLevel": 2.0
            }
        }
