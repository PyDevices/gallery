# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

"""Low-allocation pixel-art sprite and alpha-mask bank for Bit World.

Stores all multi-shade pixel-art grids and 8-bit radial alpha glow masks inside
one contiguous bytes literal wrapped in a memoryview (following the iconkit
frozen-flash pattern). At startup, unpacks scaled RGB565 sprites into a single
shared bytearray atlas and renders antialiased glows directly from memoryview
slices via FrameBuffer.blit_alpha.

Needs: pygraphics, bit_palette.

Run it:

    import bit_sprites

Tested on: unix MicroPython 1.30 (preview), CircuitPython 10.3, and CPython 3.12.
"""

from pygraphics import RGB565, FrameBuffer
from bit_palette import KEY, PALETTE_LUT

# Flat tuple of (offset, width, height) descriptors into DATA for each sprite.
SPRITE_META = (
    (0, 28, 26),     # 0: bit_body_0
    (728, 28, 26),   # 1: bit_body_1
    (1456, 16, 9),   # 2: face_neutral
    (1600, 16, 9),   # 3: face_blink
    (1744, 16, 9),   # 4: face_happy
    (1888, 16, 9),   # 5: face_love
    (2032, 16, 9),   # 6: face_sing
    (2176, 16, 9),   # 7: face_scan
    (2320, 16, 9),   # 8: face_coffee
    (2464, 16, 9),   # 9: face_sleep
    (2608, 10, 6),   # 10: flame_0
    (2668, 10, 6),   # 11: flame_1
    (2728, 10, 6),   # 12: flame_2
    (2788, 20, 18),  # 13: bit_game_right
    (3148, 16, 20),  # 14: terrarium
    (3468, 12, 11),  # 15: mug
    (3600, 11, 11),  # 16: emote_heart
    (3721, 11, 11),  # 17: emote_note
    (3842, 11, 11),  # 18: emote_sparkle
    (3963, 11, 11),  # 19: emote_bolt
    (4084, 11, 11),  # 20: emote_zzz
    (4205, 12, 14),  # 21: crystal_0
    (4373, 12, 14),  # 22: crystal_1
    (4541, 12, 14),  # 23: crystal_2
    (4709, 12, 14),  # 24: crystal_3
    (4877, 16, 14),  # 25: drone_0
    (5101, 16, 14),  # 26: drone_1
    (5325, 10, 5),   # 27: bolt
    (5375, 16, 16),  # 28: holo_bit
)

FACE_NAMES = ("neutral", "blink", "happy", "love", "sing", "scan", "coffee", "sleep")
EMOTE_NAMES = ("heart", "note", "sparkle", "bolt", "zzz")

GLOW16_OFFSET = 5631
GLOW16_SIZE = 16
GLOW24_OFFSET = 5887
GLOW24_SIZE = 24

# Adjacent bytes literals join into one constant in flash when frozen.
DATA = memoryview(
    # 0: bit_body_0 (28x26)
    b".............kl............."
    b"............jklj............"
    b".............54............."
    b".............54............."
    b"......6777777777777765......"
    b"....67887777777777776654...."
    b"...6787432222222222347654..."
    b"..677420000000000000024653.."
    b".ef7420000000000000000246dc."
    b"efg7300000000000000000036edc"
    b"efg7300000000000000000036edc"
    b"efg7300000000000000000036edc"
    b"efg7300000000000000000036edc"
    b"efg7300000000000000000036edc"
    b"efg7300000000000000000036edc"
    b".cd7300000000000000000036dc."
    b"..574200000000000000002464.."
    b"...6743222222222222223465..."
    b"....567777666fe6667777654..."
    b".....4566543222234566543...."
    b"......3454321jj12345432....."
    b".......34432iklk234432......"
    b"........23432jj234321......."
    b".........2333223332........."
    b"..........12333321.........."
    b"...........122221..........."
    # 1: bit_body_1 (28x26)
    b"............jllj............"
    b"...........ikllki..........."
    b".............65............."
    b".............54............."
    b"......6777777777777765......"
    b"....67887777777777776654...."
    b"...6787432222222222347654..."
    b".ef7742000000000000002465dc."
    b"efg7420000000000000000246edc"
    b"efg7300000000000000000036edc"
    b"efg7300000000000000000036edc"
    b"efg7300000000000000000036edc"
    b"efg7300000000000000000036edc"
    b"efg7300000000000000000036edc"
    b".cd7300000000000000000036dc."
    b"..573000000000000000000364.."
    b"..574200000000000000002464.."
    b"...6743222222222222223465..."
    b"....567777666fg6667777654..."
    b".....4566543222234566543...."
    b"......3454321kk12345432....."
    b".......34432jllk234432......"
    b"........23432kk234321......."
    b".........2333223332........."
    b"..........12333321.........."
    b"...........122221..........."
    # 2: face_neutral (16x9)
    b"................"
    b"..jkkj....jkkj.."
    b".jk88kj..jk88kj."
    b".jk8jkj..jk8jkj."
    b".jkkkkj..jkkkkj."
    b"..jkkj....jkkj.."
    b"................"
    b".....jkkkkj....."
    b"......jjjj......"
    # 3: face_blink (16x9)
    b"................"
    b"................"
    b"..jjjj....jjjj.."
    b".jkkkkj..jkkkkj."
    b".jj..jj..jj..jj."
    b"................"
    b"................"
    b".....jkkkkj....."
    b"......jjjj......"
    # 4: face_happy (16x9)
    b"................"
    b"..jkkj....jkkj.."
    b".jkkkkj..jkkkkj."
    b".kk..kk..kk..kk."
    b"................"
    b"....fggggggf...."
    b"....feeeeeef...."
    b".....feddef....."
    b"......feef......"
    # 5: face_love (16x9)
    b"................"
    b".vwwwv....vwwwv."
    b"vw8wwwv..vw8wwwv"
    b"vwwwwwv..vwwwwwv"
    b".vwwwv....vwwwv."
    b"..vwv......vwv.."
    b"................"
    b"....ukkkkkku...."
    b".....uuuuuu....."
    # 6: face_sing (16x9)
    b"................"
    b"..jkkj....jkkj.."
    b".jkkkkj..jk88kj."
    b".kk..kk..jkkkkj."
    b"..........jkkj.."
    b".....jkkkkj....."
    b"....jk0000kj...."
    b"....jk0ww0kj...."
    b".....jkkkkj....."
    # 7: face_scan (16x9)
    b".qppppppppppppq."
    b"..ppqqqqqqqqpp.."
    b".qpq88qppq88qpq."
    b".qpqqqqppqqqqpq."
    b"..pppppppppppp.."
    b"................"
    b"..pq..pqqp..qp.."
    b".....pqqqqp....."
    b"................"
    # 8: face_coffee (16x9)
    b"................"
    b"..fgge....eggf.."
    b".fg88gf..fg88gf."
    b".fggggf..fggggf."
    b"..feef....feef.."
    b"................"
    b"...fggggggggf..."
    b"....fggggggf...."
    b".....ffffff....."
    # 9: face_sleep (16x9)
    b"................"
    b"................"
    b"................"
    b"..iiii....iiii.."
    b"..hhhh....hhhh.."
    b"................"
    b"......iiii......"
    b"................"
    b"................"
    # 10: flame_0 (10x6)
    b"..jkkkkj.."
    b"..kllllk.."
    b"...kllk..."
    b"...jkkj..."
    b"....jj...."
    b"....ii...."
    # 11: flame_1 (10x6)
    b".ijkkkkji."
    b"..kllllk.."
    b"..jkllkj.."
    b"...jkkj..."
    b"...ijji..."
    b"....ii...."
    # 12: flame_2 (10x6)
    b"..fggggf.."
    b"..kllllk.."
    b"...kllk..."
    b"....kk...."
    b"....jj...."
    b".........."
    # 13: bit_game_right (20x18)
    b"........kl.........."
    b"........54.........."
    b"....67777777765....."
    b"...67874222224765..."
    b"..ef74000000000465.."
    b"..fg7300jk8k0jk836.."
    b"..fg7300jkkj0jkk36.."
    b"..ef73000000000036.."
    b"...5730000jkkj0035.."
    b"...674222222222245.."
    b"....567776fe67765..."
    b"...ef566532235654..."
    b"..efg45431kk13443..."
    b"...cd3432jllj233...."
    b"......232.kk.22....."
    b"..........jj........"
    b"..........ii........"
    b"...................."
    # 14: terrarium (16x20)
    b".....677776....."
    b"...6786ii6776..."
    b"..686ihhhhhi67.."
    b".686h..kllk..h6."
    b".66h..jkllkj..h5"
    b"68h....jkkj...h5"
    b"66h.....pp....h5"
    b"66h...qppppq..h5"
    b"66h..qppooppq.h5"
    b"66h...poooop..h5"
    b"66h....onno...h5"
    b"66h.kl..nn.fg.h5"
    b"66h.jj..nn.ee.h5"
    b"66h..oopppooo.h5"
    b".66hmmmmmmmmmh5."
    b".efggggggggggfe."
    b"efeeeeeeeeeeeefd"
    b"edccccccccccccdc"
    b".dcbbbbbbbbbbcd."
    b"..aaaaaaaaaaaa.."
    # 15: mug (12x11)
    b".ffffffff..."
    b"fggggggggf.."
    b"feeeeeeeefdd"
    b"feddddddef.d"
    b"feddggddef.d"
    b"fedgllgdef.d"
    b"feddggddefdd"
    b"feddddddef.."
    b"fecccccccf.."
    b".dcbbbbcd..."
    b"..aaaaaa...."
    # 16: emote_heart (11x11)
    b"..........."
    b".vwwv.vwwv."
    b"vw88wvw88wv"
    b"vw8wwwww8wv"
    b"vwwwwwwwwwv"
    b".vwwwwwwwv."
    b"..vwwwwwv.."
    b"...vwwwv..."
    b"....vwv...."
    b".....v....."
    b"..........."
    # 17: emote_note (11x11)
    b"....kkkkkk."
    b"....kllllk."
    b"....kk..kk."
    b"....kk..kk."
    b"....kk..kk."
    b"..kkkk..kk."
    b".kllkkikk.."
    b".kllk.kllk."
    b"..kk...kk.."
    b"..........."
    b"..........."
    # 18: emote_sparkle (11x11)
    b".....g....."
    b".....g....."
    b"...fgggf..."
    b"....ggg...."
    b"ggfgg8ggfgg"
    b".gggg8gggg."
    b"ggfgg8ggfgg"
    b"....ggg...."
    b"...fgggf..."
    b".....g....."
    b".....g....."
    # 19: emote_bolt (11x11)
    b".....gggg.."
    b"....ggff..."
    b"...ggff...."
    b"..gggggg..."
    b".ggggff...."
    b"....ggff..."
    b"...ggff...."
    b"..ggf......"
    b".gg........"
    b"..........."
    b"..........."
    # 20: emote_zzz (11x11)
    b"llllll....."
    b"...ll......"
    b"..ll......."
    b".llllll...."
    b"..........."
    b".....kkkkk."
    b".......kk.."
    b"......kk..."
    b".....kkkkk."
    b"..........."
    b"..........."
    # 21: crystal_0 (12x14)
    b".....ll....."
    b"....kllk...."
    b"...jk88kj..."
    b"..ijk88kji.."
    b".ijjkllkjji."
    b".ijkkllkkji."
    b".ijjkkkkjji."
    b"..ijkkkkji.."
    b"..ijjkkjji.."
    b"...ijjjji..."
    b"....ijji...."
    b".....ii....."
    b".....hh....."
    b"............"
    # 22: crystal_1 (12x14)
    b".....ll....."
    b"....kllk...."
    b"...tk88kt..."
    b"..stk88kts.."
    b"..stkllkts.."
    b"..stkkkkts.."
    b"..stjkkjts.."
    b"...sjkkjs..."
    b"...sjjjjs..."
    b"....sjjs...."
    b".....ss....."
    b".....rr....."
    b"............"
    b"............"
    # 23: crystal_2 (12x14)
    b".....ll....."
    b"....ukku...."
    b"...uk88ku..."
    b"...tk88kt..."
    b"...tkllkt..."
    b"...tkkkkt..."
    b"...tjkkjt..."
    b"....tkkt...."
    b"....tjjt...."
    b".....tt....."
    b".....ss....."
    b"............"
    b"............"
    b"............"
    # 24: crystal_3 (12x14)
    b".....ll....."
    b"....kllk...."
    b"...jk88kj..."
    b"..qjk88kjq.."
    b"..pjkllkjp.."
    b"..pjkkkkjp.."
    b"..pjjkkjjp.."
    b"...pjkkjp..."
    b"...pjjjjp..."
    b"....pjjp...."
    b".....pp....."
    b".....oo....."
    b"............"
    b"............"
    # 25: drone_0 (16x14)
    b".7777......7777."
    b"...4567777654..."
    b"..457777777754.."
    b".34674322347643."
    b"3464200vv0024643"
    b"356200vw8w002653"
    b"356200vwww002653"
    b"3464200vv0024643"
    b".34674322347643."
    b"..345666666543.."
    b"...2344554432..."
    b"....w..22..w...."
    b"...x........x..."
    b"................"
    # 26: drone_1 (16x14)
    b"...7777..7777..."
    b"...4567777654..."
    b"..457777777754.."
    b".34674322347643."
    b"3464200ww0024643"
    b"356200wx8x002653"
    b"356200wxxx002653"
    b"3464200ww0024643"
    b".34674322347643."
    b"..345666666543.."
    b"...2344554432..."
    b"....x..22..x...."
    b"................"
    b"................"
    # 27: bolt (10x5)
    b"..jkkkkj.."
    b".jk8888kl."
    b"ijk88888ll"
    b".jk8888kl."
    b"..jkkkkj.."
    # 28: holo_bit (16x16)
    b".......kl......."
    b".......jj......."
    b"...ijkkkkkkji..."
    b"..jkiiiiiiiiikj."
    b".jki00000000ikj."
    b"jki00ll00ll00ikj"
    b"jki00ll00ll00ikj"
    b"jki0000000000ikj"
    b"jki000kkkk000ikj"
    b".jki00000000ikj."
    b"..jkiiiiiiiiikj."
    b"...ijkkkkkkji..."
    b".....ijjjji....."
    b"......jllj......"
    b".......kk......."
    b".......ii......."
    # glow_16: 16x16 8-bit radial alpha mask (256 bytes at offset 5631)
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x03\x05\x07\x07\x05\x03\x01\x00\x00\x00\x00"
    b"\x00\x00\x00\x02\x07\x0b\x0f\x12\x12\x0f\x0b\x07\x02\x00\x00\x00\x00\x00\x02\x08\x0f\x17\x1d\x21\x21\x1d\x17\x0f\x08\x02\x00\x00"
    b"\x00\x01\x07\x0f\x1a\x25\x2e\x34\x34\x2e\x25\x1a\x0f\x07\x01\x00\x00\x03\x0b\x17\x25\x34\x42\x4b\x4b\x42\x34\x25\x17\x0b\x03\x00"
    b"\x00\x05\x0f\x1d\x2e\x42\x56\x64\x64\x56\x42\x2e\x1d\x0f\x05\x00\x00\x07\x12\x21\x34\x4b\x64\x7e\x7e\x64\x4b\x34\x21\x12\x07\x00"
    b"\x00\x07\x12\x21\x34\x4b\x64\x7e\x7e\x64\x4b\x34\x21\x12\x07\x00\x00\x05\x0f\x1d\x2e\x42\x56\x64\x64\x56\x42\x2e\x1d\x0f\x05\x00"
    b"\x00\x03\x0b\x17\x25\x34\x42\x4b\x4b\x42\x34\x25\x17\x0b\x03\x00\x00\x01\x07\x0f\x1a\x25\x2e\x34\x34\x2e\x25\x1a\x0f\x07\x01\x00"
    b"\x00\x00\x02\x08\x0f\x17\x1d\x21\x21\x1d\x17\x0f\x08\x02\x00\x00\x00\x00\x00\x02\x07\x0b\x0f\x12\x12\x0f\x0b\x07\x02\x00\x00\x00"
    b"\x00\x00\x00\x00\x01\x03\x05\x07\x07\x05\x03\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    # glow_24: 24x24 8-bit radial alpha mask (576 bytes at offset 5887)
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x02\x03\x03\x02\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x01\x03\x04\x06\x07\x08\x08\x07\x06\x04\x03\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x04\x07\x0a\x0c\x0e\x0f\x0f\x0e\x0c\x0a\x07\x04\x02\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x02\x05\x09\x0d\x11\x14\x16\x17\x17\x16\x14\x11\x0d\x09\x05\x02\x00\x00\x00\x00\x00\x00\x00\x02\x05\x0a\x0f\x14\x19\x1d\x20\x22\x22\x20\x1d\x19\x14\x0f\x0a\x05\x02\x00\x00\x00"
    b"\x00\x00\x01\x04\x09\x0f\x15\x1b\x22\x27\x2b\x2e\x2e\x2b\x27\x22\x1b\x15\x0f\x09\x04\x01\x00\x00\x00\x00\x03\x07\x0d\x14\x1b\x23\x2b\x33\x38\x3b\x3b\x38\x33\x2b\x23\x1b\x14\x0d\x07\x03\x00\x00"
    b"\x00\x01\x04\x0a\x11\x19\x22\x2b\x35\x3e\x46\x4a\x4a\x46\x3e\x35\x2b\x22\x19\x11\x0a\x04\x01\x00\x00\x02\x06\x0c\x14\x1d\x27\x33\x3e\x4a\x54\x5b\x5b\x54\x4a\x3e\x33\x27\x1d\x14\x0c\x06\x02\x00"
    b"\x00\x02\x07\x0e\x16\x20\x2b\x38\x46\x54\x62\x6c\x6c\x62\x54\x46\x38\x2b\x20\x16\x0e\x07\x02\x00\x00\x03\x08\x0f\x17\x22\x2e\x3b\x4a\x5b\x6c\x7d\x7d\x6c\x5b\x4a\x3b\x2e\x22\x17\x0f\x08\x03\x00"
    b"\x00\x03\x08\x0f\x17\x22\x2e\x3b\x4a\x5b\x6c\x7d\x7d\x6c\x5b\x4a\x3b\x2e\x22\x17\x0f\x08\x03\x00\x00\x02\x07\x0e\x16\x20\x2b\x38\x46\x54\x62\x6c\x6c\x62\x54\x46\x38\x2b\x20\x16\x0e\x07\x02\x00"
    b"\x00\x02\x06\x0c\x14\x1d\x27\x33\x3e\x4a\x54\x5b\x5b\x54\x4a\x3e\x33\x27\x1d\x14\x0c\x06\x02\x00\x00\x01\x04\x0a\x11\x19\x22\x2b\x35\x3e\x46\x4a\x4a\x46\x3e\x35\x2b\x22\x19\x11\x0a\x04\x01\x00"
    b"\x00\x00\x03\x07\x0d\x14\x1b\x23\x2b\x33\x38\x3b\x3b\x38\x33\x2b\x23\x1b\x14\x0d\x07\x03\x00\x00\x00\x00\x01\x04\x09\x0f\x15\x1b\x22\x27\x2b\x2e\x2e\x2b\x27\x22\x1b\x15\x0f\x09\x04\x01\x00\x00"
    b"\x00\x00\x00\x02\x05\x0a\x0f\x14\x19\x1d\x20\x22\x22\x20\x1d\x19\x14\x0f\x0a\x05\x02\x00\x00\x00\x00\x00\x00\x00\x02\x05\x09\x0d\x11\x14\x16\x17\x17\x16\x14\x11\x0d\x09\x05\x02\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x02\x04\x07\x0a\x0c\x0e\x0f\x0f\x0e\x0c\x0a\x07\x04\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x03\x04\x06\x07\x08\x08\x07\x06\x04\x03\x01\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x02\x03\x03\x02\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


class Sprite:
    """Wrap an RGB565 FrameBuffer view into the shared atlas with safe blit helpers."""

    def __init__(self, fb, w, h):
        self.fb = fb
        self.w = w
        self.h = h

    # Blit this sprite with color-key transparency at top-left (x, y).
    def draw(self, target_fb, x, y):
        target_fb.blit(self.fb, int(x), int(y), KEY)

    # Blit this sprite centered around (cx, cy).
    def draw_center(self, target_fb, cx, cy):
        target_fb.blit(self.fb, int(cx) - (self.w >> 1), int(cy) - (self.h >> 1), KEY)


# Unpack sprite idx from DATA into the provided memoryview slice at scale s.
def _unpack_into(meta_idx, scale, flip_x, view_slice):
    offs, src_w, src_h = SPRITE_META[meta_idx]
    s = max(1, int(scale))
    w = src_w * s
    h = src_h * s
    fb = FrameBuffer(view_slice, w, h, RGB565)
    fb.fill(KEY)
    lut = PALETTE_LUT
    src = DATA
    for ry in range(src_h):
        row_start = offs + ry * src_w
        y0 = ry * s
        rx = 0
        while rx < src_w:
            ch_byte = src[row_start + rx]
            run = 1
            while rx + run < src_w and src[row_start + rx + run] == ch_byte:
                run += 1
            if ch_byte != 46:  # 46 is ord('.')
                col = lut[ch_byte - 46]
                if col != KEY:
                    px_x = (src_w - rx - run) * s if flip_x else rx * s
                    fb.fill_rect(px_x, y0, run * s, s, col)
            rx += run
    return Sprite(fb, w, h)


class SpriteBank:
    """Unpack all scaled sprites into one shared bytearray atlas and expose glows."""

    def __init__(self, layout):
        self.layout = layout
        self.pet_px = 3 if layout.compact else 4
        self.prop_px = 2 if layout.compact else 3
        self.game_px = 2 if layout.compact else 3
        emote_px = 2

        # Build the schedule of (meta_idx, scale, flip_x) to pack into one atlas.
        specs = []
        # 0..1: bit_body
        specs.append((0, self.pet_px, False))
        specs.append((1, self.pet_px, False))
        # 2..9: bit_faces
        for i in range(2, 10):
            specs.append((i, self.pet_px, False))
        # 10..12: thruster flames
        for i in range(10, 13):
            specs.append((i, self.pet_px, False))
        # 13..14: bit_game_r and bit_game_l
        specs.append((13, self.game_px, False))
        specs.append((13, self.game_px, True))
        # 15..16: terrarium and mug
        specs.append((14, self.prop_px, False))
        specs.append((15, self.prop_px, False))
        # 17..21: 5 emotes
        for i in range(16, 21):
            specs.append((i, emote_px, False))
        # 22..25: 4 crystal frames
        for i in range(21, 25):
            specs.append((i, self.game_px, False))
        # 26..27: 2 drone frames
        for i in range(25, 27):
            specs.append((i, self.game_px, False))
        # 28..29: bolt and holo_bit
        specs.append((27, self.game_px, False))
        specs.append((28, self.prop_px, False))

        # Compute total atlas bytes so we make only a single bytearray allocation.
        total_bytes = 0
        for meta_idx, sc, _ in specs:
            _, sw, sh = SPRITE_META[meta_idx]
            total_bytes += (sw * sc) * (sh * sc) * 2

        self.atlas_buf = bytearray(total_bytes)
        self.atlas_mv = memoryview(self.atlas_buf)

        unpacked = []
        cursor = 0
        for meta_idx, sc, flip in specs:
            _, sw, sh = SPRITE_META[meta_idx]
            nbytes = (sw * sc) * (sh * sc) * 2
            sub_mv = self.atlas_mv[cursor : cursor + nbytes]
            unpacked.append(_unpack_into(meta_idx, sc, flip, sub_mv))
            cursor += nbytes

        self.bit_body = (unpacked[0], unpacked[1])
        self.bit_faces = {}
        for idx, name in enumerate(FACE_NAMES):
            self.bit_faces[name] = unpacked[2 + idx]
        self.flames = (unpacked[10], unpacked[11], unpacked[12])
        self.bit_game_r = unpacked[13]
        self.bit_game_l = unpacked[14]
        self.terrarium = unpacked[15]
        self.mug = unpacked[16]

        self.emotes = {}
        for idx, name in enumerate(EMOTE_NAMES):
            self.emotes[name] = unpacked[17 + idx]

        self.crystals = (unpacked[22], unpacked[23], unpacked[24], unpacked[25])
        self.drones = (unpacked[26], unpacked[27])
        self.bolt = unpacked[28]
        self.holo_bit = unpacked[29]

        # Zero-copy memoryview slices for 8-bit radial alpha glow masks.
        self.glow16 = DATA[GLOW16_OFFSET : GLOW16_OFFSET + GLOW16_SIZE * GLOW16_SIZE]
        self.glow24 = DATA[GLOW24_OFFSET : GLOW24_OFFSET + GLOW24_SIZE * GLOW24_SIZE]

    # Blend a soft 8-bit radial glow centered at (cx, cy) via FrameBuffer.blit_alpha.
    def draw_glow(self, fb, cx, cy, color, large=True):
        if large:
            fb.blit_alpha(
                self.glow24,
                int(cx) - (GLOW24_SIZE >> 1),
                int(cy) - (GLOW24_SIZE >> 1),
                GLOW24_SIZE,
                GLOW24_SIZE,
                color,
            )
        else:
            fb.blit_alpha(
                self.glow16,
                int(cx) - (GLOW16_SIZE >> 1),
                int(cy) - (GLOW16_SIZE >> 1),
                GLOW16_SIZE,
                GLOW16_SIZE,
                color,
            )

    # Render the full Workshop Bit character with soft thruster glow and eye tracking.
    def draw_workshop_bit(self, fb, cx, cy, frame_idx, mood="neutral", look_dx=0, look_dy=0, glow_col=None):
        body = self.bit_body[frame_idx & 1]
        bx = int(cx) - (body.w >> 1)
        by = int(cy) - (body.h >> 1)
        flame = self.flames[frame_idx % len(self.flames)]
        flame_cy = by + body.h - self.pet_px + (flame.h >> 1)
        if glow_col is not None:
            self.draw_glow(fb, cx, flame_cy, glow_col, large=True)
            self.draw_glow(fb, cx, by + 2 * self.pet_px, glow_col, large=False)
        flame.draw(fb, int(cx) - (flame.w >> 1), by + body.h - self.pet_px)
        body.draw(fb, bx, by)
        face = self.bit_faces.get(mood, self.bit_faces["neutral"])
        max_dx = self.pet_px * 2
        max_dy = self.pet_px
        fdx = max(-max_dx, min(max_dx, int(look_dx)))
        fdy = max(-max_dy, min(max_dy, int(look_dy)))
        fx = bx + 6 * self.pet_px + fdx
        fy = by + 8 * self.pet_px + fdy
        face.draw(fb, fx, fy)
