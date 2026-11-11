#!/usr/bin/env python3
"""Build de_blue_mesa: original GoldSrc geometry, WAD3 textures and previews.

Requires Python 3.10+, Pillow and NumPy. No game assets are redistributed.
Run from any directory. Geometry uses Valve 220 MAP texture coordinates.
"""
from pathlib import Path
import base64
import json
import math
import random
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source'
PREVIEW = ROOT / 'preview'
# The released name carries the version. A player joining a game downloads only
# the files they don't have, and is refused outright if they have an older map
# under the same name. So each release gets a new name, and everyone's copy
# updates by itself when they join. Bump MAP_VERSION for every release.
MAP_VERSION = 'v2'
MAP_NAME = f'de_blue_mesa_{MAP_VERSION}'
# The map's own sounds are versioned for the same reason, but separately: bump
# SOUND_VERSION only when a sound changes, so players don't re-download the rest.
SOUND_VERSION = 'v1'
SOUND_DIR = f'bluemesa/{SOUND_VERSION}'
TEX = {}
BRUSHES = []
ENTITIES = []
BUILDINGS = []   # (x0, y0, x1, y1, tag) of every building(), for the overview
RNG = np.random.default_rng(1609)

# All display wording lives here so the map can be renamed without touching art code.
# These are original names in the spirit of the setting, not trademarked branding.
LORE = {
    'chicken_name': 'HERMANOS',
    'chicken_sub': 'CHICKEN  /  DESERT RECIPE',
    'law_name': 'BETTER CALL SAM',
    'law_sub': 'LAW OFFICES  /  505-BEST-LAW',
    'law_door': 'S. GOODWIN, ATTORNEY',
    'house_number': '312',
    'house_street': 'NEGRA MESA LN',
    'poster_top': 'HAVE YOU SEEN',
    'poster_name': 'THIS MAN',
    'board_title': 'PERSONS OF INTEREST',
    'lab_sign': 'AUTHORIZED PERSONNEL ONLY',
    'lab_sub': 'SUB-LEVEL 1  /  RESPIRATOR REQUIRED',
    'caution_top': 'CAUTION',
    'caution_sub': 'CHEMICAL PROCESS AREA',
}


def font(size, bold=True):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans' + ('-Bold' if bold else '') + '.ttf',
        'C:/Windows/Fonts/' + ('arialbd.ttf' if bold else 'arial.ttf'),
        '/System/Library/Fonts/Helvetica.ttc',
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def noise_texture(name, color, amount=8, size=(128, 128)):
    w, h = size
    noise = RNG.normal(0, amount, (h, w, 1))
    im = Image.fromarray(np.uint8(np.clip(np.array(color)[None, None, :] + noise, 0, 255)))
    TEX[name] = im
    return im, ImageDraw.Draw(im)


def centered(draw, text, y, width, size, color):
    f = font(size)
    bounds = draw.textbbox((0, 0), text, font=f)
    draw.text(((width - (bounds[2] - bounds[0])) / 2, y - bounds[1]), text, font=f, fill=color)


def weather(name, grime=.22, streaks=10, base=.30, seed=0):
    """Multiply grime, run-off streaks and a ground-line dirt band over a finished texture."""
    im = TEX[name]
    w, h = im.size
    a = np.array(im, dtype=np.float32)
    rng = np.random.default_rng(1609 + seed)
    small = rng.random((max(2, h // 16), max(2, w // 16))).astype(np.float32)
    blot = np.asarray(Image.fromarray(np.uint8(small * 255)).resize((w, h), Image.Resampling.BICUBIC),
                      dtype=np.float32) / 255.
    a *= (1.0 - grime * blot)[:, :, None]
    for _ in range(streaks):
        x = int(rng.integers(0, w))
        ln = int(rng.integers(h // 4, h))
        wd = int(rng.integers(1, 4))
        fade = np.linspace(1.0 - grime * .9, 1.0, ln).astype(np.float32)
        a[:ln, x:min(x + wd, w)] *= fade[:, None, None]
    band = max(4, h // 6)
    grad = np.linspace(1.0 - base, 1.0, band).astype(np.float32)[::-1]
    a[h - band:] *= grad[:, None, None]
    TEX[name] = Image.fromarray(np.uint8(np.clip(a, 0, 255)))


def figure(d, cx, top, scale, color):
    """Flat head-and-shoulders silhouette used for posters, portraits and the board."""
    r = int(6 * scale)
    d.ellipse((cx - r, top, cx + r, top + 2 * r), fill=color)
    neck = top + 2 * r
    d.polygon([(cx - int(11 * scale), neck + int(13 * scale)), (cx - int(7 * scale), neck + int(2 * scale)),
               (cx + int(7 * scale), neck + int(2 * scale)), (cx + int(11 * scale), neck + int(13 * scale))],
              fill=color)


def framed(name, size, mat, frame, inner, border=8):
    """A picture-frame plate: outer frame, mat, and a recessed inner panel."""
    im = Image.new('RGB', size, frame)
    d = ImageDraw.Draw(im)
    d.rectangle((border, border, size[0] - border - 1, size[1] - border - 1), fill=mat)
    d.rectangle((border + 3, border + 3, size[0] - border - 4, size[1] - border - 4), fill=inner)
    TEX[name] = im
    return im, d


def make_theme_textures():
    """Landmark branding, wall art and the surfaces the new rooms need."""
    y, r, cream = (232, 191, 46), (176, 47, 42), (243, 236, 214)
    # --- Hermanos chicken: storefront sign, rooftop logo, menu board ---
    for name, size, big in [('bm_pollos', (256, 64), 24), ('bm_pollos_lg', (256, 128), 26)]:
        im = Image.new('RGB', size, y)
        d = ImageDraw.Draw(im)
        d.rectangle((2, 2, size[0] - 3, size[1] - 3), outline=r, width=4)
        cy = 10 if size[1] == 64 else 14
        # rooster: body, tail sweep, head and comb
        d.ellipse((18, cy + 8, 54, cy + 40), fill=r)
        d.polygon([(16, cy + 24), (2, cy + 6), (10, cy + 34)], fill=r)
        d.ellipse((44, cy + 2, 62, cy + 20), fill=r)
        d.polygon([(50, cy + 2), (54, cy - 8), (58, cy + 2)], fill=r)
        d.polygon([(60, cy + 10), (70, cy + 13), (60, cy + 16)], fill=(214, 130, 40))
        centered(d, LORE['chicken_name'], cy + 2, size[0] + 60, big, r)
        centered(d, LORE['chicken_sub'], size[1] - 20, size[0] + 60, 10, (92, 58, 30))
        TEX[name] = im
    im = Image.new('RGB', (128, 256), (38, 40, 36))
    d = ImageDraw.Draw(im)
    d.rectangle((4, 4, 123, 251), outline=(150, 150, 140), width=3)
    centered(d, 'MENU', 12, 128, 20, y)
    for i, (item, price) in enumerate([('CURLY FRIES', '1.75'), ('2 PC BASKET', '4.25'), ('FAMILY BOX', '9.50'),
                                       ('SLAW', '1.25'), ('ICED TEA', '1.00'), ('DESERT MELT', '5.75'),
                                       ('WINGS x8', '6.00'), ('SODA', '1.10')]):
        row = 46 + i * 25
        d.text((12, row), item, font=font(10, False), fill=cream)
        d.text((96, row), price, font=font(10), fill=y)
        d.line((10, row + 17, 118, row + 17), fill=(70, 72, 66))
    TEX['bm_menu'] = im
    # --- Law office: highway billboard, storefront glazing, panelled backdrop, diplomas ---
    im = Image.new('RGB', (256, 128), cream)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 255, 127), outline=(52, 78, 132), width=5)
    d.rectangle((0, 96, 255, 127), fill=(52, 78, 132))
    figure(d, 34, 28, 1.8, (63, 70, 82))
    centered(d, LORE['law_name'], 20, 306, 19, (176, 36, 40))
    centered(d, 'NOW!', 50, 306, 24, (52, 78, 132))
    centered(d, LORE['law_sub'], 104, 256, 12, cream)
    TEX['bm_saul_ad'] = im
    im, d = noise_texture('bm_saul_win', (56, 84, 88), 3, (256, 128))
    d.rectangle((4, 4, 251, 123), outline=(178, 172, 142), width=6)
    d.polygon([(20, 4), (86, 4), (152, 123), (86, 123)], fill=(78, 112, 116))
    centered(d, LORE['law_door'], 44, 256, 15, (236, 226, 186))
    centered(d, LORE['law_sub'], 68, 256, 10, (222, 208, 160))
    TEX['bm_saul_win'] = im
    # Cheap strip-mall office: pale green above a dark wainscot and chair rail.
    im, d = noise_texture('bm_law_wall', (168, 176, 150), 4)
    d.rectangle((0, 78, 127, 127), fill=(84, 66, 48))
    d.rectangle((0, 72, 127, 80), fill=(112, 90, 64))
    d.line((0, 74, 127, 74), fill=(148, 122, 88))
    for x in range(0, 128, 24):
        d.line((x, 82, x, 127), fill=(68, 54, 39), width=2)
    TEX['bm_law_wall'] = im
    im, d = noise_texture('bm_diploma', (74, 59, 45), 4)
    for cx in (2, 66):
        for cy in (2, 66):
            d.rectangle((cx, cy, cx + 58, cy + 58), fill=(46, 36, 28))
            d.rectangle((cx + 5, cy + 5, cx + 53, cy + 53), fill=(226, 217, 184))
            for ln in range(4):
                d.line((cx + 12, cy + 18 + ln * 8, cx + 46, cy + 18 + ln * 8), fill=(148, 138, 112))
            d.ellipse((cx + 38, cy + 38, cx + 50, cy + 50), fill=(168, 52, 46))
    TEX['bm_diploma'] = im
    # --- House: number plate, garage door, shingles, brick, pool ---
    im = Image.new('RGB', (128, 64), (196, 186, 152))
    d = ImageDraw.Draw(im)
    d.rectangle((3, 3, 124, 60), outline=(72, 66, 52), width=3)
    centered(d, LORE['house_number'], 8, 128, 26, (56, 52, 42))
    centered(d, LORE['house_street'], 42, 128, 10, (86, 78, 60))
    TEX['bm_housenum'] = im
    im, d = noise_texture('bm_garage', (188, 180, 154), 4, (128, 256))
    for row in range(0, 256, 32):
        d.rectangle((0, row, 127, row + 3), fill=(126, 120, 100))
        d.line((0, row + 5, 127, row + 5), fill=(212, 205, 178))
    d.rectangle((2, 2, 125, 253), outline=(140, 133, 111), width=3)
    TEX['bm_garage'] = im
    im, d = noise_texture('bm_shingle', (122, 96, 78), 6)
    for row in range(0, 128, 16):
        off = (row // 16 % 2) * 16
        d.line((0, row, 127, row), fill=(88, 68, 56), width=2)
        for x in range(off, 128, 32):
            d.line((x, row, x, row + 16), fill=(94, 74, 60))
    TEX['bm_shingle'] = im
    im, d = noise_texture('bm_brick', (146, 96, 74), 6)
    for row in range(0, 128, 16):
        off = (row // 16 % 2) * 16
        d.line((0, row, 127, row), fill=(178, 168, 150), width=3)
        for x in range(off, 128, 32):
            d.line((x, row, x, row + 16), fill=(178, 168, 150), width=3)
    TEX['bm_brick'] = im
    im, d = noise_texture('bm_pool', (58, 128, 150), 4)
    for n in range(0, 128, 16):
        d.arc((n - 24, n - 12, n + 40, n + 28), 200, 340, fill=(112, 176, 190), width=3)
    d.rectangle((0, 0, 127, 5), fill=(196, 206, 198))
    TEX['bm_pool'] = im
    # --- Character / investigation wall art ---
    im, d = framed('bm_hat', (128, 128), (196, 188, 158), (52, 48, 44), (206, 198, 170))
    d.polygon([(30, 54), (98, 54), (94, 44), (34, 44)], fill=(38, 36, 34))   # hat brim
    d.polygon([(42, 44), (86, 44), (82, 24), (46, 24)], fill=(38, 36, 34))   # crown
    d.rectangle((44, 60, 60, 72), outline=(38, 36, 34), width=3)             # glasses
    d.rectangle((68, 60, 84, 72), outline=(38, 36, 34), width=3)
    d.line((60, 66, 68, 66), fill=(38, 36, 34), width=3)
    d.polygon([(42, 98), (47, 80), (81, 80), (86, 98)], fill=(38, 36, 34))
    centered(d, LORE['poster_name'], 101, 128, 12, (52, 48, 44))
    im, d = noise_texture('bm_dea', (156, 122, 78), 7, (256, 256))
    d.rectangle((3, 3, 252, 252), outline=(94, 70, 44), width=6)
    centered(d, LORE['board_title'], 14, 256, 16, (58, 46, 32))
    spots = [(24, 44), (100, 44), (176, 44), (24, 150), (100, 150), (176, 150)]
    for i, (px, py) in enumerate(spots):
        d.rectangle((px, py, px + 56, py + 72), fill=(226, 221, 204), outline=(120, 112, 92), width=2)
        figure(d, px + 28, py + 10, 1.5, (108, 116, 124) if i % 2 else (92, 88, 96))
        d.rectangle((px + 4, py + 58, px + 52, py + 68), fill=(196, 190, 172))
        d.ellipse((px + 24, py - 5, px + 32, py + 3), fill=(178, 44, 40))
    for a, b in [(0, 4), (1, 3), (2, 5), (1, 4)]:
        d.line((spots[a][0] + 28, spots[a][1], spots[b][0] + 28, spots[b][1]), fill=(178, 44, 40), width=2)
    TEX['bm_dea'] = im
    im, d = framed('bm_missing', (128, 128), (232, 228, 210), (232, 228, 210), (232, 228, 210), 4)
    d.rectangle((4, 4, 123, 123), outline=(120, 112, 92), width=2)
    centered(d, LORE['poster_top'], 10, 128, 12, (168, 44, 40))
    d.rectangle((34, 30, 94, 86), fill=(206, 200, 182), outline=(120, 112, 92), width=2)
    figure(d, 64, 38, 1.9, (96, 100, 108))
    centered(d, LORE['poster_name'], 92, 128, 13, (52, 48, 42))
    centered(d, 'CALL 505-0199', 110, 128, 9, (92, 86, 70))
    for i, (fr, mt, shirt) in enumerate([((92, 72, 52), (238, 232, 212), (78, 108, 142)),
                                         ((64, 62, 58), (226, 224, 208), (150, 96, 84)),
                                         ((110, 92, 60), (240, 234, 210), (96, 128, 96))]):
        im, d = framed(f'bm_photo{i + 1}', (128, 128), mt, fr, (188, 196, 190), 10)
        d.rectangle((14, 78, 113, 113), fill=(172, 158, 128))
        figure(d, 64, 30, 2.4, shirt)
        d.ellipse((44, 26, 84, 62), fill=(214, 178, 146))
    # --- Surfaces for the rethemed interiors ---
    im, d = noise_texture('bm_checker', (222, 216, 196), 3)
    for cy in range(0, 128, 32):
        for cx in range(0, 128, 32):
            if (cx // 32 + cy // 32) % 2:
                d.rectangle((cx, cy, cx + 31, cy + 31), fill=(58, 62, 60))
    TEX['bm_checker'] = im
    im, d = noise_texture('bm_booth', (142, 46, 44), 5)
    for row in range(0, 128, 24):
        d.line((0, row, 127, row), fill=(104, 32, 32), width=3)
        d.line((0, row + 3, 127, row + 3), fill=(174, 68, 62))
    TEX['bm_booth'] = im
    im, d = noise_texture('bm_fryer', (158, 166, 162), 4)
    d.rectangle((6, 6, 121, 58), fill=(74, 80, 80), outline=(196, 202, 196), width=3)
    for kx in range(18, 116, 24):
        d.ellipse((kx, 70, kx + 14, 84), fill=(58, 62, 62), outline=(206, 210, 202), width=2)
    d.rectangle((10, 96, 117, 118), fill=(96, 102, 100), outline=(186, 190, 184), width=2)
    TEX['bm_fryer'] = im
    im, d = noise_texture('bm_carpet', (86, 78, 92), 6)
    for _ in range(900):
        px, py = RNG.integers(0, 128, 2)
        d.point((int(px), int(py)), fill=(104, 96, 110))
    TEX['bm_carpet'] = im
    im, d = noise_texture('bm_panel', (128, 96, 64), 5)
    for x in range(0, 128, 21):
        d.line((x, 0, x, 127), fill=(88, 64, 42), width=2)
        d.line((x + 3, 0, x + 3, 127), fill=(152, 118, 80))
    TEX['bm_panel'] = im
    im, d = noise_texture('bm_vending', (168, 44, 42), 4, (128, 256))
    d.rectangle((6, 6, 121, 154), fill=(46, 62, 68), outline=(206, 200, 176), width=4)
    for sy in range(22, 150, 32):
        d.line((12, sy, 115, sy), fill=(150, 148, 132), width=2)
        for sx in range(18, 112, 22):
            d.rectangle((sx, sy - 18, sx + 14, sy - 2), fill=(206, 176, 62) if (sx + sy) % 3 else (96, 150, 178))
    centered(d, 'ICE COLD', 172, 128, 15, (244, 238, 214))
    d.rectangle((22, 196, 105, 240), fill=(56, 50, 46), outline=(200, 194, 172), width=3)
    TEX['bm_vending'] = im
    im, d = noise_texture('bm_fridge', (176, 186, 184), 4, (128, 256))
    d.rectangle((8, 8, 119, 247), fill=(64, 92, 98), outline=(214, 218, 208), width=5)
    for sy in range(40, 240, 48):
        d.line((14, sy, 113, sy), fill=(198, 204, 198), width=3)
        for sx in range(20, 110, 20):
            d.rectangle((sx, sy - 26, sx + 13, sy - 4), fill=(150, 176, 148))
    TEX['bm_fridge'] = im


def make_lab_textures():
    """Surfaces and signage for the underground superlab."""
    steel, dark, warn = (188, 194, 190), (48, 56, 58), (232, 191, 46)
    # Clean-room wall panels with a rail and a scuffed kick strip.
    im, d = noise_texture('bm_labwall', (206, 212, 206), 4)
    for x in range(0, 128, 32):
        d.line((x, 0, x, 127), fill=(172, 180, 176), width=2)
        d.line((x + 2, 0, x + 2, 127), fill=(226, 230, 224))
    d.rectangle((0, 58, 127, 66), fill=(150, 160, 158))
    d.rectangle((0, 112, 127, 127), fill=(126, 136, 136))
    TEX['bm_labwall'] = im
    # Sealed epoxy floor, faintly gridded.
    im, d = noise_texture('bm_labfloor', (118, 130, 128), 5)
    for n in range(0, 128, 64):
        d.line((n, 0, n, 127), fill=(98, 110, 110), width=2)
        d.line((0, n, 127, n), fill=(98, 110, 110), width=2)
    for _ in range(260):
        px, py = RNG.integers(0, 128, 2)
        d.point((int(px), int(py)), fill=(142, 152, 148))
    TEX['bm_labfloor'] = im
    # Fume hood: glass sash over a lit working area.
    im, d = noise_texture('bm_fume', (176, 184, 182), 3, (128, 256))
    d.rectangle((6, 6, 121, 150), fill=(96, 138, 140), outline=(214, 220, 212), width=5)
    d.polygon([(16, 6), (60, 6), (120, 108), (76, 108)], fill=(126, 168, 168))
    for sx in range(24, 110, 28):
        d.rectangle((sx, 96, sx + 14, 144), fill=(196, 214, 200), outline=(74, 96, 98), width=2)
    d.rectangle((10, 158, 117, 176), fill=(84, 92, 94))
    d.rectangle((6, 182, 121, 249), fill=(158, 166, 164), outline=(120, 130, 130), width=3)
    for ky in (200, 226):
        for kx in range(22, 110, 26):
            d.ellipse((kx, ky, kx + 12, ky + 12), fill=(70, 80, 82))
    TEX['bm_fume'] = im
    # Reactor shell: banded stainless with rivet lines.
    im, d = noise_texture('bm_reactor', steel, 4)
    for y in (10, 62, 114):
        d.rectangle((0, y, 127, y + 9), fill=(140, 148, 148))
        d.line((0, y + 1, 127, y + 1), fill=(228, 232, 228))
        for rx in range(8, 128, 20):
            d.ellipse((rx, y + 2, rx + 5, y + 7), fill=(96, 104, 106))
    for x in range(0, 128, 42):
        d.line((x, 0, x, 127), fill=(160, 168, 166), width=2)
    TEX['bm_reactor'] = im
    # Wire mesh over shadow, for the chemical cage.
    im, d = noise_texture('bm_cage', (58, 64, 62), 3)
    for n in range(0, 128, 16):
        d.line((n, 0, n, 127), fill=(150, 156, 150), width=2)
        d.line((0, n, 127, n), fill=(150, 156, 150), width=2)
    for n in range(0, 128, 64):
        d.line((n, 0, n, 127), fill=(178, 182, 174), width=4)
    TEX['bm_cage'] = im
    # Spiral-ribbed ventilation ducting.
    im, d = noise_texture('bm_duct', (162, 168, 166), 4)
    for y in range(0, 128, 12):
        d.line((0, y, 127, y), fill=(120, 128, 128), width=3)
        d.line((0, y + 4, 127, y + 4), fill=(198, 202, 196))
    TEX['bm_duct'] = im
    # Hazmat suits hanging on a rail.
    im, d = noise_texture('bm_hazmat', (96, 104, 106), 4, (128, 256))
    d.rectangle((0, 8, 127, 16), fill=(150, 158, 156))
    for sx in (10, 50, 90):
        d.line((sx + 14, 16, sx + 14, 34), fill=(178, 184, 180), width=3)
        d.ellipse((sx + 4, 30, sx + 26, 52), fill=(214, 186, 62))
        d.ellipse((sx + 9, 35, sx + 21, 47), fill=(120, 150, 156))
        d.polygon([(sx, 96), (sx + 2, 50), (sx + 26, 50), (sx + 28, 96)], fill=(226, 196, 66))
        d.polygon([(sx + 2, 96), (sx + 6, 200), (sx + 22, 200), (sx + 26, 96)], fill=(214, 184, 58))
        d.rectangle((sx + 4, 118, sx + 24, 128), fill=(150, 128, 44))
    TEX['bm_hazmat'] = im
    # Control-room monitor bank.
    im, d = noise_texture('bm_monitor', (52, 58, 60), 3)
    for my in (6, 68):
        for mx in (6, 68):
            d.rectangle((mx, my, mx + 54, my + 54), fill=(28, 32, 34), outline=(104, 112, 112), width=3)
            d.rectangle((mx + 6, my + 6, mx + 48, my + 42), fill=(46, 92, 88))
            for ln in range(3):
                d.line((mx + 10, my + 12 + ln * 9, mx + 44, my + 12 + ln * 9), fill=(122, 196, 168))
            d.ellipse((mx + 46, my + 46, mx + 51, my + 51), fill=(196, 84, 66))
    TEX['bm_monitor'] = im
    # Chemical drum with a hazard band.
    im, d = noise_texture('bm_barrel', (74, 108, 132), 5)
    for y in (16, 100):
        d.rectangle((0, y, 127, y + 12), fill=(52, 78, 98))
        d.line((0, y + 2, 127, y + 2), fill=(140, 168, 182))
    d.rectangle((0, 50, 127, 84), fill=warn)
    d.polygon([(64, 56), (78, 80), (50, 80)], fill=dark)
    d.rectangle((62, 64, 66, 73), fill=warn)
    TEX['bm_barrel'] = im
    # Elevator car: brushed panel with a call plate.
    im, d = noise_texture('bm_elevator', (150, 158, 158), 4, (128, 256))
    d.rectangle((4, 4, 123, 251), outline=(96, 104, 106), width=5)
    d.line((64, 8, 64, 247), fill=(104, 112, 112), width=4)
    for px in (34, 84):
        d.rectangle((px - 10, 108, px + 10, 148), fill=(70, 78, 80))
        d.ellipse((px - 5, 118, px + 5, 128), fill=(214, 186, 62))
    TEX['bm_elevator'] = im
    # Lift call button: a yellow push-button on a steel plate, arrows up and down.
    im, d = noise_texture('bm_callbtn', (70, 78, 80), 3, (64, 64))
    d.rectangle((2, 2, 61, 61), outline=(150, 158, 156), width=3)
    d.ellipse((18, 18, 46, 46), fill=warn, outline=(38, 42, 40), width=3)
    d.polygon([(32, 5), (40, 14), (24, 14)], fill=(222, 232, 226))
    d.polygon([(32, 59), (40, 50), (24, 50)], fill=(222, 232, 226))
    TEX['bm_callbtn'] = im
    # Two wall placards.
    for name, top, sub, bg, fg in [
            ('bm_labsign', LORE['lab_sign'], LORE['lab_sub'], (44, 76, 92), (222, 232, 226)),
            ('bm_caution', LORE['caution_top'], LORE['caution_sub'], warn, (38, 42, 40))]:
        im = Image.new('RGB', (256, 64), bg)
        d = ImageDraw.Draw(im)
        d.rectangle((3, 3, 252, 60), outline=fg, width=3)
        centered(d, top, 11, 256, 20 if len(top) < 12 else (15 if len(top) < 20 else 12), fg)
        centered(d, sub, 40, 256, 10, fg)
        TEX[name] = im


SIGN_COLOURS = {'A': (236, 137, 77), 'B': (82, 168, 180)}   # the overview's A and B colours


def make_wayfinding_textures():
    """Lane materials and painted A / B direction signs.

    Each route has its own wall material so players can tell at a glance which
    one they are in: red canyon rock on Long, whitewash in Mid and the B alley,
    corrugated metal on the east route, timber on the CT side.
    """
    # Long: layered red sandstone.
    im, d = noise_texture('bm_canyon', (164, 84, 58), 9)
    for y in range(0, 128, 18):
        pts = [(x, y + int(4 * math.sin(x / 19 + y))) for x in range(0, 129, 8)]
        d.line(pts, fill=(128, 60, 42), width=3)
        d.line([(x, z + 5) for x, z in pts], fill=(196, 112, 78), width=2)
    # Mid: whitewashed plaster over a blue-grey plinth.
    im, d = noise_texture('bm_whitewash', (222, 216, 202), 6)
    d.rectangle((0, 104, 127, 127), fill=(96, 118, 132))
    d.line((0, 103, 127, 103), fill=(70, 88, 100), width=2)
    for _ in range(6):
        cx, cy = RNG.integers(8, 120, 2)
        d.ellipse((int(cx) - 7, int(cy) - 4, int(cx) + 7, int(cy) + 4), fill=(194, 184, 164))
    # East: corrugated iron, ribbed, streaked with rust.
    im, d = noise_texture('bm_corrugated', (132, 140, 142), 5)
    for x in range(0, 128, 8):
        d.line((x, 0, x, 127), fill=(96, 104, 108), width=2)
        d.line((x + 3, 0, x + 3, 127), fill=(170, 176, 176))
    for x in (18, 58, 98):
        d.rectangle((x, 70, x + 6, 127), fill=(128, 82, 56))
    # The A-side water tower's tank: pale steel with the A colour banded round it.
    im, d = noise_texture('bm_tower', (176, 190, 192), 4)
    d.rectangle((0, 44, 127, 84), fill=SIGN_COLOURS['A'])
    d.line((0, 44, 127, 44), fill=(90, 96, 98), width=2)
    d.line((0, 84, 127, 84), fill=(90, 96, 98), width=2)
    # Direction signs: a painted panel with the site letter and an arrow.
    arrows = {'u': [(32, 34), (46, 48), (38, 48), (38, 60), (26, 60), (26, 48), (18, 48)],
              'd': [(32, 60), (46, 46), (38, 46), (38, 34), (26, 34), (26, 46), (18, 46)],
              'l': [(14, 47), (28, 35), (28, 43), (50, 43), (50, 51), (28, 51), (28, 59)],
              'r': [(50, 47), (36, 35), (36, 43), (14, 43), (14, 51), (36, 51), (36, 59)]}
    for site, c in SIGN_COLOURS.items():
        for k, pts in arrows.items():
            im = Image.new('RGB', (64, 64), c)
            d = ImageDraw.Draw(im)
            d.rectangle((1, 1, 62, 62), outline=(24, 28, 28), width=3)
            centered(d, site, 2, 64, 26, (250, 248, 238))
            d.polygon(pts, fill=(250, 248, 238), outline=(24, 28, 28))
            TEX[f'bm_dir_{site.lower()}_{k}'] = im


def make_textures():
    im, d = noise_texture('bm_sand', (167, 126, 82), 9, (256, 256))
    for _ in range(420):
        x, y = RNG.integers(0, 256, 2)
        c = random.Random(int(x * 256 + y)).choice([(136, 103, 72), (184, 143, 94), (148, 112, 74)])
        d.line((int(x), int(y), int(x + 2), int(y)), fill=c)
    im, d = noise_texture('bm_rock', (148, 97, 61), 8, (256, 256))
    for y in range(0, 256, 25):
        pts = [(x, y + int(3 * math.sin(x / 35 + y))) for x in range(0, 257, 8)]
        d.line(pts, fill=(123, 77, 48), width=2)
        d.line([(x, z+4) for x, z in pts], fill=(168, 113, 72), width=2)
    noise_texture('bm_stucco', (191, 165, 120), 7)
    noise_texture('bm_teal', (57, 107, 103), 5)
    noise_texture('bm_cream', (215, 208, 171), 4)
    noise_texture('bm_rust', (126, 73, 49), 8)
    noise_texture('bm_black', (33, 36, 33), 4)
    noise_texture('bm_concrete', (131, 132, 118), 7)
    im, d = noise_texture('bm_asphalt', (66, 69, 63), 6, (256, 256))
    for _ in range(500):
        x, y = RNG.integers(0, 256, 2)
        d.point((int(x),int(y)), fill=(104, 103, 85))
    im, d = noise_texture('bm_metal', (112, 132, 127), 4)
    for x in range(0, 128, 16):
        d.rectangle((x, 0, x + 3, 127), fill=(80, 101, 98))
        d.line((x + 5, 0, x + 5, 127), fill=(140, 153, 142))
    im, d = noise_texture('bm_blue', (65, 117, 142), 5)
    for y in (8, 112):
        d.rectangle((0, y, 127, y + 7), fill=(44, 71, 75))
        d.line((0, y+1, 127, y+1), fill=(132, 153, 145))
    im, d = noise_texture('bm_wood', (139, 108, 72), 5)
    for y in range(0, 128, 24):
        d.line((0,y,127,y), fill=(77,68,49), width=3)
        for x in (8, 116): d.ellipse((x,y+8,x+3,y+11), fill=(51,57,49))
    for _ in range(40):
        x, y = RNG.integers(0,128,2)
        d.line((int(x),int(y),int(min(x+24,127)),int(y)),fill=(113,87,59))
    im, d = noise_texture('bm_crate', (129, 113, 74), 4)
    for x in (0, 42, 84, 126): d.line((x,0,x,127), fill=(64,66,47), width=3)
    d.rectangle((3,3,124,124),outline=(173,147,91),width=10)
    d.line((12,12,115,115), fill=(174,144,88),width=11)
    im, d = noise_texture('bm_roof', (112, 100, 77), 5)
    for y in range(0,128,32):
        d.line((0,y,127,y),fill=(83,81,64),width=2)
        for x in range((y//32 % 2)*32,128,64):
            d.line((x,y,x,y+32),fill=(83,81,64),width=2)
    im, d = noise_texture('bm_tile', (142, 166, 157), 3)
    for n in range(0,128,32):
        d.line((n,0,n,127),fill=(78,103,101),width=2)
        d.line((0,n,127,n),fill=(78,103,101),width=2)
    im, d = noise_texture('bm_glass', (58, 96, 103), 2)
    d.polygon([(0,0),(72,0),(128,57),(128,90),(37,0)], fill=(87,129,132))
    d.rectangle((0,0,127,127),outline=(34,59,64),width=5)
    im, d = noise_texture('bm_window', (49, 75, 76), 2)
    d.rectangle((3,3,124,124),outline=(168,163,133),width=7)
    d.line((64,8,64,120),fill=(169,164,134),width=4)
    for y in range(20,120,14): d.line((10,y,118,y),fill=(89,106,101),width=3)
    im, d = noise_texture('bm_door', (65,100,95), 5)
    d.rectangle((7,5,120,124),outline=(135,148,124),width=5)
    d.rectangle((23,20,106,81),outline=(36,69,66),width=3)
    d.ellipse((101,89,109,97),fill=(190,164,100))
    im, d = noise_texture('bm_rvstripe', (210,203,169), 3)
    d.rectangle((0,64,127,91),fill=(160,100,42))
    d.rectangle((0,94,127,108),fill=(102,106,79))
    for y in (15,42,121): d.line((0,y,127,y),fill=(179,177,145),width=1)
    im, d = noise_texture('bm_washer', (157,176,165), 4)
    d.rectangle((3,3,124,124),outline=(76,99,96),width=4)
    d.rectangle((11,10,116,30),fill=(44,69,68))
    d.ellipse((89,14,101,26),fill=(185,156,82))
    d.ellipse((24,39,104,119),fill=(55,76,75),outline=(208,217,191),width=7)
    d.ellipse((37,52,91,106),fill=(50,86,94))
    d.arc((43,56,85,100),210,350,fill=(119,145,141),width=7)
    im, d = noise_texture('bm_pump', (176,169,139), 3)
    d.rectangle((9,8,118,56), fill=(34,56,51))
    centered(d,'MESA',12,128,15,(189,208,157))
    centered(d,'087.9',33,128,14,(205,221,162))
    d.rectangle((0,77,127,127),fill=(151,70,47))
    centered(d,'FUEL',88,128,24,(231,211,153))
    im, d = noise_texture('bm_hazard', (190,155,53), 3)
    for x in range(-128,256,48):
        d.polygon([(x,0),(x+20,0),(x+148,128),(x+128,128)],fill=(42,53,48))
    im, d = noise_texture('bm_bed', (135,133,87), 4)
    for y in range(0,128,16): d.rectangle((0,y,127,y+5),fill=(79,105,85))
    for name, text, sub, bg, fg in [
        ('bm_motel','MESA MOTOR INN','VACANCY  /  AIR COOLED', (44,94,87),(227,206,145)),
        ('bm_laundry','BLUE MESA','INDUSTRIAL LAUNDRY', (56,93,101),(212,219,184)),
        ('bm_fuelsign','MESA FUEL','SERVICE  /  GAS  /  ICE', (135,63,43),(236,210,150)),
        ('bm_rvsign','PRIVATE PROPERTY','KEEP OUT', (211,183,119),(67,66,49)),
    ]:
        im = Image.new('RGB',(256,64),bg); d=ImageDraw.Draw(im)
        d.rectangle((2,2,253,61),outline=fg,width=2)
        centered(d,text,12,256,22 if len(text)<15 else 19,fg)
        centered(d,sub,42,256,10,fg)
        TEX[name]=im
    # The author's credit: a board at each spawn and a licence plate on the RV.
    im = Image.new('RGB',(256,64),(211,183,119)); d=ImageDraw.Draw(im)
    d.rectangle((2,2,253,61),outline=(67,66,49),width=2)
    centered(d,'BLUE MESA',8,256,22,(67,66,49)); centered(d,'A MAP BY YAMAN',38,256,14,(120,60,40))
    TEX['bm_credit']=im
    im = Image.new('RGB',(64,32),(232,226,200)); d=ImageDraw.Draw(im)
    d.rectangle((1,1,62,30),outline=(40,70,120),width=2); centered(d,'YAMAN',7,64,14,(40,70,120))
    TEX['bm_plate']=im
    for name,letter,c in [('bm_sitea','A',(197,92,48)),('bm_siteb','B',(82,140,153))]:
        im,d=noise_texture(name,(130,125,99),6,(256,256))
        d.ellipse((20,20,236,236),outline=c,width=13)
        centered(d,letter,64,256,140,c)
    make_theme_textures()
    make_lab_textures()
    # Adobe for the lane walls: rendered mud over brick, cracked off in patches.
    # Drawn last so the shared noise sequence of every earlier texture is unchanged.
    im, d = noise_texture('bm_adobe', (184, 150, 108), 8)
    for px, py, pw, ph in [(8, 18, 30, 20), (74, 60, 40, 26), (22, 92, 26, 18), (96, 8, 22, 16)]:
        d.rectangle((px, py, px + pw, py + ph), fill=(150, 98, 72))
        for row in range(py, py + ph, 8):
            d.line((px, row, px + pw, row), fill=(176, 158, 132))
    d.rectangle((0, 0, 127, 5), fill=(160, 128, 90))
    d.line((0, 6, 127, 6), fill=(206, 176, 132))
    # Boombox front for the RV radio: two speakers either side of a tape deck.
    im, d = noise_texture('bm_radio', (54, 56, 58), 3, (128, 64))
    for cx in (22, 106):
        d.ellipse((cx - 19, 13, cx + 19, 51), fill=(30, 31, 32), outline=(150, 152, 150), width=2)
        d.ellipse((cx - 10, 22, cx + 10, 42), fill=(62, 64, 66))
        d.ellipse((cx - 3, 29, cx + 3, 35), fill=(150, 152, 150))
    d.rectangle((46, 10, 82, 26), fill=(40, 70, 64), outline=(150, 152, 150))
    d.text((49, 13), '505FM', font=font(9), fill=(150, 230, 190))
    d.rectangle((46, 32, 82, 50), fill=(26, 27, 28), outline=(120, 122, 120))
    for bx in range(47, 82, 7):
        d.rectangle((bx, 54, bx + 5, 60), fill=(170, 172, 168))
    make_wayfinding_textures()
    # Grime, run-off and a ground-line dirt band so the flat base surfaces sit
    # alongside the printed art instead of reading as untouched paint.
    for i, (name, grime, streaks, base) in enumerate([
            ('bm_stucco', .26, 14, .34), ('bm_metal', .20, 10, .30), ('bm_concrete', .24, 8, .34),
            ('bm_tile', .16, 6, .26), ('bm_cream', .18, 9, .28), ('bm_roof', .22, 5, .24),
            ('bm_rust', .28, 12, .30), ('bm_door', .18, 6, .26), ('bm_brick', .24, 10, .32),
            ('bm_shingle', .20, 4, .22), ('bm_panel', .16, 7, .28), ('bm_checker', .14, 5, .24),
            ('bm_garage', .22, 9, .30), ('bm_washer', .14, 5, .20), ('bm_pump', .16, 6, .24),
            ('bm_labwall', .18, 8, .30), ('bm_labfloor', .20, 6, .22), ('bm_reactor', .14, 7, .24),
            ('bm_duct', .16, 5, .20), ('bm_elevator', .16, 6, .26), ('bm_cage', .12, 4, .20),
            ('bm_adobe', .24, 12, .36), ('bm_canyon', .20, 8, .30), ('bm_whitewash', .20, 14, .34),
            ('bm_corrugated', .22, 12, .30)]):
        weather(name, grime, streaks, base, seed=i)
    for name,c in [('sky',(98,152,167)),('NULL',(204,60,160)),('AAATRIGGER',(198,107,31)),('CLIP',(193,47,155))]:
        TEX[name]=Image.new('RGB',(16,16),c)


def write_wad():
    data=bytearray(b'WAD3'+b'\0'*8); directory=[]
    for name, im in TEX.items():
        assert len(name.encode()) < 16
        p=im.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
        w,h=im.size
        levels=[p]
        for n in range(1,4):
            levels.append(im.resize((w>>n,h>>n),Image.Resampling.LANCZOS).quantize(palette=p,dither=Image.Dither.NONE))
        offsets=[]; cursor=40
        for lev in levels:
            offsets.append(cursor); cursor+=lev.width*lev.height
        lump=bytearray(struct.pack('<16s6I',name.encode(),w,h,*offsets))
        for lev in levels: lump+=lev.tobytes()
        pal=bytes((p.getpalette()+[0]*768)[:768])
        lump+=struct.pack('<H',256)+pal+b'\0\0'
        pos=len(data);data+=lump
        directory.append(struct.pack('<iiiBBH16s',pos,len(lump),len(lump),0x43,0,0,name.encode()))
    off=len(data)
    data+=b''.join(directory)
    struct.pack_into('<ii',data,4,len(directory),off)
    (SOURCE/'bluemesa.wad').write_bytes(data)


def point(classname, origin=None, **keys):
    e={'classname':classname,**{k:str(v) for k,v in keys.items()}}
    if origin is not None:e['origin']=' '.join(str(v) for v in origin)
    ENTITIES.append({'keys':e,'brushes':[]})
    return len(ENTITIES)-1


def brush_entity(classname, **keys):
    return point(classname,None,**keys)


def add_brush(polys,texture,tag,entity=0,solid=True,faces=None):
    b={'faces':[],'tag':tag,'entity':entity,'solid':solid}
    for i,poly in enumerate(polys):
        v=np.array(poly,dtype=float)
        n=np.cross(v[1]-v[0],v[2]-v[0]);n/=np.linalg.norm(n)
        face={'points':[[round(float(c),4) for c in p] for p in poly],
              'texture':(faces or {}).get(i,texture),'normal':list(n)}
        b['faces'].append(face)
    vertices=np.array([p for f in b['faces'] for p in f['points']])
    b['min']=vertices.min(axis=0).tolist();b['max']=vertices.max(axis=0).tolist()
    BRUSHES.append(b);ENTITIES[entity]['brushes'].append(len(BRUSHES)-1)
    return b


def box(x0,y0,z0,x1,y1,z1,texture='bm_stucco',tag='structure',entity=0,solid=True,faces=None):
    assert x1>x0 and y1>y0 and z1>z0,(x0,y0,z0,x1,y1,z1,tag)
    polys=[[(x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)],
           [(x1,y1,z0),(x1,y1,z1),(x1,y0,z1),(x1,y0,z0)],
           [(x1,y0,z0),(x1,y0,z1),(x0,y0,z1),(x0,y0,z0)],
           [(x0,y1,z0),(x0,y1,z1),(x1,y1,z1),(x1,y1,z0)],
           [(x0,y1,z0),(x1,y1,z0),(x1,y0,z0),(x0,y0,z0)],
           [(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]]
    return add_brush(polys,texture,tag,entity,solid,faces)


def slab_with_holes(x0,y0,z0,x1,y1,z1,holes,texture='bm_sand',tag='ground',side='bm_concrete'):
    """Emit a slab as convex boxes around rectangular (hx0,hy0,hx1,hy1) cutouts.

    The slab is split into Y bands at every hole edge, then each band is split
    along X, so every emitted piece stays an axis-aligned box. Side faces get
    `side`: the only ones that survive compilation are those facing into a hole
    (piece-to-piece seams are culled, outer edges fall outside the sealed hull),
    so the shafts read as lined concrete rather than raw sand.
    """
    faces={0:side,1:side,2:side,3:side}
    edges=sorted({y0,y1}|{v for h in holes for v in (h[1],h[3]) if y0<v<y1})
    pieces=[]
    for ya,yb in zip(edges,edges[1:]):
        row=sorted((h for h in holes if h[1]<yb and h[3]>ya),key=lambda a:a[0])
        cursor=x0
        for hx0,_,hx1,_ in row:
            if hx0>cursor:pieces.append(box(cursor,ya,z0,hx0,yb,z1,texture,tag,faces=faces))
            cursor=max(cursor,hx1)
        if cursor<x1:pieces.append(box(cursor,ya,z0,x1,yb,z1,texture,tag,faces=faces))
    return pieces


def stair_run(x0,x1,y_start,z_start,steps,rise=16,run=24,direction=1,base=-288,
              texture='bm_concrete',tag='stair'):
    """A straight flight of treads, each a box standing on `base`.

    Tread i sits at z_start - rise*i, so direction=1 descends toward +Y and
    direction=-1 descends toward -Y. Returns the (y, z) the flight ends at.
    """
    for i in range(steps):
        ya=y_start+direction*i*run
        yb=ya+direction*run
        box(x0,min(ya,yb),base,x1,max(ya,yb),z_start-rise*i,texture,tag)
    return y_start+direction*steps*run, z_start-rise*(steps-1)


def smooth_stair(x0,x1,y0,z_top=0,z_bottom=-288,tag='stairwell'):
    """A straight flight descending toward +Y, with an invisible ramp over it.

    Treads of 16 x 24 from z_top down to one step above z_bottom. The CLIP wedge
    lies on the plane through every nosing, so walking down it is one smooth
    slope (about 34 degrees) instead of a string of 16-unit drops. Returns the
    y where the last tread ends.
    """
    steps=(z_top-z_bottom)//16
    end,_=stair_run(x0,x1,y0,z_top,steps,direction=1,base=z_bottom,tag=tag)
    top,toe=y0+24,y0+24+24*steps
    add_brush([[(x0,top,z_bottom),(x0,top,z_top),(x0,toe,z_bottom)],
               [(x1,toe,z_bottom),(x1,top,z_top),(x1,top,z_bottom)],
               [(x0,toe,z_bottom),(x1,toe,z_bottom),(x1,top,z_bottom),(x0,top,z_bottom)],
               [(x1,top,z_bottom),(x1,top,z_top),(x0,top,z_top),(x0,top,z_bottom)],
               [(x0,top,z_top),(x1,top,z_top),(x1,toe,z_bottom),(x0,toe,z_bottom)]],
              'CLIP',tag+' clip ramp')
    return end


def cylinder(cx,cy,z0,z1,r,texture='bm_blue',tag='tank',sides=8,entity=0):
    pts=[(round(cx+r*math.cos(2*math.pi*i/sides),3),round(cy+r*math.sin(2*math.pi*i/sides),3)) for i in range(sides)]
    polys=[[(x,y,z0) for x,y in reversed(pts)],[(x,y,z1) for x,y in pts]]
    for i,(x,y) in enumerate(pts):
        x2,y2=pts[(i+1)%sides]
        polys.append([(x,y,z0),(x2,y2,z0),(x2,y2,z1),(x,y,z1)])
    return add_brush(polys,texture,tag,entity)


def wheel(cx,y0,y1,cz=32,r=32):
    pts=[(round(cx+r*math.cos(2*math.pi*i/8),3),round(cz+r*math.sin(2*math.pi*i/8),3)) for i in range(8)]
    # Looking down -Y, the XZ ring has outward normal -Y.
    polys=[[(x,y0,z) for x,z in pts],[(x,y1,z) for x,z in reversed(pts)]]
    for i,(x,z) in enumerate(pts):
        xx,zz=pts[(i+1)%8]
        polys.append([(x,y0,z),(x,y1,z),(xx,y1,zz),(xx,y0,zz)])
    return add_brush(polys,'bm_black','RV wheels')


def plaque(x0,y,z0,w,h,texture,tag='sign'):
    b=box(x0,y,z0,x0+w,y+4,z0+h,'bm_metal',tag,faces={2:texture})
    tw,th=TEX[texture].size;su=w/tw;sv=h/th
    b['faces'][2]['uv']=[[1,0,0,-x0/su],[0,0,-1,(z0+h)/sv],su,sv]


# box() face order: 0:-X 1:+X 2:-Y 3:+Y 4:-Z 5:+Z
FACING = {'-y': 2, '+y': 3, '-x': 0, '+x': 1}


def wall_art(x, y, z, w, h, texture, facing='-y', tag='wall art', entity=0, backing='bm_metal'):
    """Hang a picture of arbitrary world size on a wall of any of the four orientations.

    (x, y, z) is the lower-left corner as seen by a player looking at the face.
    Width runs along the wall, height runs up; the texture is stretched to fit.
    """
    idx = FACING[facing]
    tw, th = TEX[texture].size
    if facing in ('-y', '+y'):
        y0 = y if facing == '-y' else y - 4
        b = box(x, y0, z, x + w, y0 + 4, z + h, backing, tag, entity, faces={idx: texture})
        su, sv = w / tw, h / th
        u = [1, 0, 0, -x / su] if facing == '-y' else [-1, 0, 0, (x + w) / su]
    else:
        x0 = x if facing == '-x' else x - 4
        b = box(x0, y, z, x0 + 4, y + w, z + h, backing, tag, entity, faces={idx: texture})
        su, sv = w / tw, h / th
        u = [0, -1, 0, (y + w) / su] if facing == '-x' else [0, 1, 0, -y / su]
    b['faces'][idx]['uv'] = [u, [0, 0, -1, (z + h) / sv], su, sv]
    # The back and edges are left undrawn to save lightmap space; any of them that
    # turns out not to be covered is drawn again by reveal_exposed_faces().
    b['backing'] = backing
    for i in range(6):
        if i != idx:
            b['faces'][i]['texture'] = 'NULL'
    return b


def clip(x0, y0, z0, x1, y1, z1):
    """Invisible collision smoothing over stairs, kerbs and prop clusters."""
    return box(x0, y0, z0, x1, y1, z1, 'CLIP', 'clip')


def null_faces(brush, *indices):
    """Blank faces that are permanently buried, to keep lightmap allocation down."""
    for i in indices:
        brush['faces'][i]['texture'] = 'NULL'
    return brush


def furnish(x0, y0, z0, x1, y1, z1, body, top, tag, thickness=6, entity=0):
    """A carcass plus a contrasting worktop - desks, counters, benches and booths."""
    box(x0, y0, z0, x1, y1, z1 - thickness, body, tag, entity)
    return box(x0 - 4, y0 - 4, z1 - thickness, x1 + 4, y1 + 4, z1, top, tag + ' top', entity)


def floor_decal(x,y,size,texture):
    b=box(x,y,0,x+size,y+size,1,texture,'site marking')
    tw,th=TEX[texture].size;s=size/tw
    b['faces'][5]['uv']=[[1,0,0,-x/s],[0,-1,0,(y+size)/s],s,s]


def wall_y(y,x0,x1,height,texture,doors=(),z0=0,tag='wall'):
    cursor=x0
    for a,b,h in sorted(doors):
        if a>cursor:box(cursor,y,z0,a,y+16,z0+height,texture,tag)
        if h<height:box(a,y,z0+h,b,y+16,z0+height,texture,tag)
        cursor=b
    if cursor<x1:box(cursor,y,z0,x1,y+16,z0+height,texture,tag)


def wall_x(x,y0,y1,height,texture,doors=(),z0=0,tag='wall'):
    cursor=y0
    for a,b,h in sorted(doors):
        if a>cursor:box(x,cursor,z0,x+16,a,z0+height,texture,tag)
        if h<height:box(x,a,z0+h,x+16,b,z0+height,texture,tag)
        cursor=b
    if cursor<y1:box(x,cursor,z0,x+16,y1,z0+height,texture,tag)


SILL = 48


def building(x0,y0,x1,y1,h,texture,tag,doors=None,windows=None,
             light='236 220 170 240',roof='bm_roof',glass='bm_window',breakable=()):
    """Four walls, a roof and a ceiling light.

    doors:     {side: [(a, b, opening_height), ...]}  gap from the floor up
    windows:   {side: [(a, b), ...]}                  gap between SILL and head
    breakable: sides whose windows are shootable glass rather than solid panes
    Spans run along X for south/north and along Y for west/east.
    """
    BUILDINGS.append((x0, y0, x1, y1, tag))
    doors = {k: list(v) for k, v in (doors or {}).items()}
    windows = windows or {}
    head = min(112, h - 24)
    # A window is a full-height gap in the wall run, then filled back in below and above.
    gaps = {side: doors.get(side, []) + [(a, b, h) for a, b in windows.get(side, ())]
            for side in ('south', 'north', 'west', 'east')}
    wall_y(y0,x0,x1,h,texture,gaps['south'],tag=tag)
    wall_y(y1-16,x0,x1,h,texture,gaps['north'],tag=tag)
    wall_x(x0,y0+16,y1-16,h,texture,gaps['west'],tag=tag)
    wall_x(x1-16,y0+16,y1-16,h,texture,gaps['east'],tag=tag)
    for side, spans in windows.items():
        for a, b in spans:
            pane = 0
            if side in breakable:
                pane = brush_entity('func_breakable',material='0',health='20',rendermode='2',
                                    renderamt='130',rendercolor='110 156 161')
            if side in ('south', 'north'):
                wy = y0 if side == 'south' else y1 - 16
                box(a,wy,0,b,wy+16,SILL,texture,tag+' sill')
                box(a,wy,head,b,wy+16,h,texture,tag+' head')
                box(a+2,wy+6,SILL,b-2,wy+10,head,glass,tag+' window',pane)
            else:
                wx = x0 if side == 'west' else x1 - 16
                box(wx,a,0,wx+16,b,SILL,texture,tag+' sill')
                box(wx,a,head,wx+16,b,h,texture,tag+' head')
                box(wx+6,a+2,SILL,wx+10,b-2,head,glass,tag+' window',pane)
    box(x0-8,y0-8,h,x1+8,y1+8,h+16,roof,tag+' roof')
    point('light',((x0+x1)//2,(y0+y1)//2,h-24),_light=light)


# --- The superlab, beneath the laundry -------------------------------------
# Floor top, ceiling underside, and the interior footprint of the room.
LAB_FLOOR, LAB_CEIL = -288, -80
LAB_X0, LAB_Y0, LAB_X1, LAB_Y1 = 600, 376, 1504, 1120
# Where each descent pierces the ground slab (x0, y0, x1, y1).
# Sized for four riders: the car's standing area is 152 x 96.
HOLE_ELEVATOR = (616, 976, 776, 1104)
# One straight flight, 128 wide, straight ahead of the laundry's south door. The
# opening runs until a player on the ramp has 72 units under the lab ceiling.
HOLE_STAIRS   = (960, 392, 1088, 704)
# The east stair: same width and pitch as the main one, inside the blockhouse,
# running north under the laundry's south wall and into the lab.
HOLE_TUNNEL   = (1152, -72, 1280, 216)
# CT drop hatch beside the laundry's north door: one way down, straight onto site B.
HOLE_HATCH    = (1256, 1040, 1336, 1120)
DESCENT_HOLES = [HOLE_ELEVATOR, HOLE_STAIRS, HOLE_TUNNEL, HOLE_HATCH]
# Doorway through the superlab's south wall at the foot of the east stair.
TUNNEL_DOOR = (1152, 1280)
SITE_B_MARK = (1120, 750, 1360, 990)   # the painted plant zone, round the reactor


def superlab():
    """Sealed room under the laundry, its three descents, and its contents."""
    w='bm_labwall'
    dx0,dx1=TUNNEL_DOOR
    # Shell. Walls run from the floor up to the underside of the ground slab so
    # the volume is closed; the south wall is split around the tunnel mouth.
    box(584,360,-304,1520,1136,LAB_FLOOR,'bm_labfloor','superlab floor')
    # The ceiling is pierced where the lift and the stairwell come down, or the
    # descents would arrive in a gap too short to stand up in.
    slab_with_holes(LAB_X0,LAB_Y0,LAB_CEIL,LAB_X1,LAB_Y1,-64,
                    [HOLE_ELEVATOR,HOLE_STAIRS,HOLE_HATCH],w,'superlab ceiling',side=w)
    box(584,360,LAB_FLOOR,LAB_X0,1136,-64,w,'superlab wall')
    box(LAB_X1,360,LAB_FLOOR,1520,1136,-64,w,'superlab wall')
    box(LAB_X0,1120,LAB_FLOOR,LAB_X1,1136,-64,w,'superlab wall')
    box(LAB_X0,360,LAB_FLOOR,dx0,LAB_Y0,-64,w,'superlab wall')
    box(dx1,360,LAB_FLOOR,LAB_X1,LAB_Y0,-64,w,'superlab wall')
    box(dx0,360,-160,dx1,LAB_Y0,-64,w,'superlab wall')

    # --- D1: the lift in the north washer bay ------------------------------
    # A flat car flush with the laundry floor, with a washer console on its back
    # edge. Use-only and toggled: press E on it to ride, and it stays where it
    # stops; a call button on each floor fetches it. wait >= 0 makes a blocked
    # car reverse instead of stalling on whoever is standing under it.
    ex0,ey0,ex1,ey1=HOLE_ELEVATOR
    for lx0,ly0,lx1,ly1 in [(ex0-16,ey0-16,ex0,ey1+16),(ex1,ey0-16,ex1+16,ey1+16),
                            (ex0,ey1,ex1,ey1+16)]:
        box(lx0,ly0,LAB_FLOOR,lx1,ly1,-64,'bm_elevator','elevator shaft')
    # The south face is open at the bottom, or the car would arrive in a sealed
    # box with no way out into the room.
    box(ex0,ey0-16,-160,ex1,ey0,-64,'bm_elevator','elevator shaft')
    car_top,console=2,56
    # A door travels its own height minus lip, so lip sets the car top down
    # exactly onto the lab floor.
    travel=car_top-LAB_FLOOR
    lip=(16+console)-travel
    # GoldSrc doors take movesnd / stopsnd, not Quake's `sounds`. 6 is the looping
    # "large rollers" run, 1 a braking clang: the ride is heard on both floors, so
    # "someone is coming" is information both teams can act on. 288 = toggle + use only.
    eid=brush_entity('func_door',targetname='lift',angle='-2',speed='150',wait='1',lip=str(lip),
                     spawnflags='288',movesnd='6',stopsnd='1')
    box(ex0+4,ey0+4,car_top-16,ex1-4,ey1-4,car_top,'bm_elevator','elevator platform',eid)
    b=box(ex0+4,ey1-28,car_top,ex1-4,ey1-4,car_top+console,'bm_elevator','elevator washer console',
          eid,faces={2:'bm_washer'})
    su,sv=(ex1-ex0-8)/128,console/128
    b['faces'][2]['uv']=[[1,0,0,-(ex0+4)/su],[0,0,-1,(car_top+console)/sv],su,sv]
    # Call buttons: on the laundry's north wall beside the shaft, and on the
    # lab's west wall just south of where the car opens.
    for bx0,by0,bz0,bx1,by1,face in [(ex1+24,1132,car_top+44,ex1+56,1136,2),
                                     (LAB_X0,ey0-80,LAB_FLOOR+44,LAB_X0+4,ey0-48,1)]:
        bid=brush_entity('func_button',target='lift',spawnflags='1',wait='1',sounds='9')
        b=box(bx0,by0,bz0,bx1,by1,bz0+32,'bm_metal','lift call button',bid,faces={face:'bm_callbtn'})
        w=(bx1-bx0) if face==2 else (by1-by0)
        u=[1,0,0,-bx0/(w/64)] if face==2 else [0,1,0,-by0/(w/64)]
        b['faces'][face]['uv']=[u,[0,0,-1,(bz0+32)/.5],w/64,.5]
    wall_art(ex0+32,ey0-20,-156,96,32,'bm_labsign','-y','lift sign')

    # --- D2: one straight stair, straight ahead of the laundry's south door --
    # Eighteen 16-unit treads under an invisible ramp through their nosings, so
    # the walk down is one smooth slope. Hazard-striped rails keep anyone from
    # stepping off the sides, and a hanging sign faces the door.
    sx0,sy0,sx1,sy1=HOLE_STAIRS
    toe=smooth_stair(sx0,sx1,sy0,0,LAB_FLOOR)
    # The flight starts 16 north of the lab's south wall; close that slot.
    box(sx0,LAB_Y0,LAB_FLOOR,sx1,sy0,LAB_CEIL,'bm_labwall','stair foot')
    for rx0,ry0,rx1,ry1 in [(sx0-16,sy0,sx0,sy1+16),(sx1,sy0,sx1+16,sy1+16),(sx0,sy1,sx1,sy1+16)]:
        box(rx0,ry0,2,rx1,ry1,42,'bm_hazard','stairwell railing')
        clip(rx0,ry0,42,rx1,ry1,128)   # no hopping the rail into the stairwell: the hatch is the drop
    wall_art(sx0+16,sy1,96,sx1-sx0-32,40,'bm_labsign','-y','stairwell sign')
    for rx in (sx0+20,sx1-24):
        box(rx,sy1,136,rx+4,sy1+4,224,'bm_metal','sign hanger')
    point('light',((sx0+sx1)//2,sy0+140,150),_light='214 232 228 170')
    point('light',((sx0+sx1)//2,toe-40,-120),_light='214 232 228 150')

    # --- D3: the east stair, inside the blockhouse --------------------------
    # The east route's own full-width way down: the same 128-wide smooth flight
    # as the main stair, so ten attackers are not queuing for one staircase.
    # It runs north under the laundry's south wall and lands at the lab's
    # south doorway, beside the plant zone. Past the opening its ceiling is the
    # underside of the ground, 64 down, which the ramp clears with headroom.
    tx0,ty0,tx1,ty1=HOLE_TUNNEL
    end=smooth_stair(tx0,tx1,ty0,0,LAB_FLOOR,tag='east stair')
    box(tx0-16,ty0-16,-304,tx1+16,LAB_Y0,LAB_FLOOR,'bm_labfloor','east stair floor')
    for wx0,wx1 in [(tx0-16,tx0),(tx1,tx1+16)]:
        box(wx0,ty0-16,LAB_FLOOR,wx1,LAB_Y0,-64,'bm_concrete','east stair wall')
    box(tx0,ty0-16,LAB_FLOOR,tx1,ty0,0,'bm_concrete','east stair wall')
    point('light',((tx0+tx1)//2,ty0+60,90),_light='214 226 220 190')
    point('light',((tx0+tx1)//2,end-80,-150),_light='198 214 216 150')
    # The blockhouse over it, door facing the scrapyard.
    building(tx0-32,ty0-48,tx1+32,ty1+16,128,'bm_concrete','access head',
             {'south':[(tx0,tx1,112)]},light='214 226 220 220',roof='bm_roof')
    wall_art(tx0-36,ty0-8,56,176,40,'bm_caution','-x','blockhouse sign')

    # --- Bomb site B ------------------------------------------------------
    # The plant floor sits east of where the stair lands, between the reactor and
    # the tunnel mouth, so each descent arrives at a different side of it.
    mx0,my0,mx1,my1=SITE_B_MARK
    b=box(mx0,my0,LAB_FLOOR,mx1,my1,LAB_FLOOR+1,'bm_siteb','site marking')
    sc=(mx1-mx0)/256
    b['faces'][5]['uv']=[[1,0,0,-mx0/sc],[0,-1,0,my1/sc],sc,sc]
    for hx0,hy0,hx1,hy1 in [(mx0-16,my0-16,mx1+16,my0),(mx0-16,my1,mx1+16,my1+16),
                            (mx0-16,my0,mx0,my1),(mx1,my0,mx1+16,my1)]:
        box(hx0,hy0,LAB_FLOOR,hx1,hy1,LAB_FLOOR+1,'bm_hazard','site striping')
    eid=brush_entity('func_bomb_target')
    box(mx0-80,my0-80,LAB_FLOOR,mx1+60,my1+160,-160,'AAATRIGGER','B bomb site',eid,False)
    # Crouch-high cover for the planter, on the open side away from the reactor.
    box(1288,776,LAB_FLOOR,1352,840,LAB_FLOOR+44,'bm_crate','B plant pallet')
    # The landing under the CT hatch: stepping off the kerb is a 210-unit fall
    # onto it, about 17 HP, instead of 45 HP all the way to the floor.
    box(*HOLE_HATCH[:2],LAB_FLOOR,*HOLE_HATCH[2:],LAB_FLOOR+96,'bm_crate','hatch landing')

    # --- Superlab interior -------------------------------------------------
    # Reactor column: the main piece of cover on the plant floor.
    cylinder(1180,900,LAB_FLOOR,-148,56,'bm_reactor','reactor vessel')
    clip(1124,844,LAB_FLOOR,1236,956,-148)
    cylinder(1180,900,-148,-132,46,'bm_metal','reactor head')
    cylinder(1180,900,-132,LAB_CEIL,16,'bm_duct','reactor vent')
    cylinder(780,860,LAB_FLOOR,-180,40,'bm_reactor','condenser')
    clip(740,820,LAB_FLOOR,820,900,-180)
    cylinder(780,860,-180,-168,32,'bm_metal','condenser head')
    for cy in (622,674):                # touching, and against the control desk
        cylinder(700,cy,LAB_FLOOR,-216,26,'bm_barrel','solvent drum')
    clip(674,596,LAB_FLOOR,726,700,-216)
    # Fume hood run down the east wall.
    for fy in (520,648,776):           # one continuous run, no gaps between hoods
        box(1440,fy,LAB_FLOOR,1504,fy+128,-140,'bm_labwall','fume hood')
        wall_art(1440,fy+4,LAB_FLOOR+4,120,144,'bm_fume','-x','fume hood front')
        point('light',(1410,fy+64,-150),_light='188 226 220 130')
    # Benches with breakable glassware along the south wall, either side of the stair.
    for bx in (656,1312):             # against the south wall; the east one clears the east stair
        furnish(bx,LAB_Y0,LAB_FLOOR,bx+192,LAB_Y0+72,LAB_FLOOR+44,'bm_metal','bm_cream','lab bench')
        eid=brush_entity('func_breakable',material='0',health='12',rendermode='2',
                         renderamt='140',rendercolor='150 190 190')
        cylinder(bx+56,LAB_Y0+36,LAB_FLOOR+44,LAB_FLOOR+80,14,'bm_glass','labware',entity=eid)
        cylinder(bx+136,LAB_Y0+36,LAB_FLOOR+44,LAB_FLOOR+72,12,'bm_glass','labware')
        clip(bx,LAB_Y0,LAB_FLOOR,bx+192,LAB_Y0+72,LAB_FLOOR+80)
    # Caged chemical store beside the elevator.
    # Its west side is against the lift shaft and its back against the north wall.
    for gx0,gy0,gx1,gy1 in [(792,976,808,1120),(1080,976,1096,1120),(808,1104,1080,1120)]:
        box(gx0,gy0,LAB_FLOOR,gx1,gy1,-140,'bm_cage','chemical cage')
    for bx in (834,886,938,990):         # drums touching, leaving a clear 64 to the east side
        cylinder(bx,1078,LAB_FLOOR,-224,26,'bm_barrel','stored drum')
    clip(808,1052,LAB_FLOOR,1016,1104,-224)
    # Control nook in the south-west corner.
    furnish(LAB_X0,520,LAB_FLOOR,LAB_X0+144,592,LAB_FLOOR+44,'bm_metal','bm_panel','control desk')
    wall_art(LAB_X0+4,512,LAB_FLOOR+52,88,88,'bm_monitor','+x','monitor bank')   # on the wall itself
    wall_art(LAB_X0+4,616,LAB_FLOOR+52,88,88,'bm_monitor','+x','monitor bank')
    # Locker room detail and signage.
    wall_art(LAB_X0+4,700,LAB_FLOOR+8,128,192,'bm_hazmat','+x','hazmat lockers')
    wall_art(1096,1116,LAB_FLOOR+72,160,40,'bm_labsign','-y','lab placard')
    wall_art(1300,380,LAB_FLOOR+72,160,40,'bm_caution','+y','lab placard')
    # Overhead services and extractor fans.
    box(640,932,-108,1464,956,LAB_CEIL,'bm_duct','extract duct')
    box(1240,392,-108,1264,932,LAB_CEIL,'bm_duct','extract duct')
    for fx,fy in [(880,944),(1360,944)]:
        cylinder(fx,fy,-124,-108,34,'bm_metal','extractor fan')
    # Lighting: the room is sealed from the sky, so every lumen is placed here.
    # A 3 x 3 grid; the middle column clears the stair, and the north-west light
    # sits south of the lift shaft rather than inside it.
    for lx,ly in [(760,520),(760,760),(700,920),(1140,520),(1140,760),(1140,1000),
                  (1400,520),(1400,760),(1400,1000)]:
        point('light',(lx,ly,-104),_light='226 236 232 210')
    point('light',(1180,900,-120),_light='168 220 208 170')


def crate(x,y,z=0,size=80):
    box(x,y,z,x+size,y+size,z+size,'bm_crate','crates')


# --- Lanes -------------------------------------------------------------------
# Taller than a standing player plus a teammate boost, so a lane can't be skipped.
WALL_H = 192


# Route materials: which one a wall face shows says which route it belongs to.
LONG, MID, EAST, CTW = 'bm_canyon', 'bm_whitewash', 'bm_corrugated', 'bm_wood'
_SIDE = {'-x': 0, '+x': 1, '-y': 2, '+y': 3}


def lane_wall(x0, y0, x1, y1, h=WALL_H, texture=MID, tag='lane wall', sides=None):
    """A lane wall; `sides` gives individual faces ('-x', '+x', '-y', '+y')
    their own material, so each side matches the route it faces."""
    faces = {_SIDE[k]: v for k, v in (sides or {}).items()}
    return box(x0, y0, 0, x1, y1, h, texture, tag, faces=faces)


def cliff(x0, y0, x1, y1, h, tag='rock mass'):
    """A rock mass as a stepped cliff rather than one flat-faced block.

    A full-footprint base, an upper tier set back 24 from every edge, and two
    boulders on top. The base is at least 140 high, so its ledge is out of
    reach even with a teammate boost (58 + 72 = 130).
    """
    base = max(140, int(h * .7))
    box(x0, y0, 0, x1, y1, base, 'bm_rock', tag)
    inset = 24
    box(x0 + inset, y0 + inset, base, x1 - inset, y1 - inset, h, 'bm_rock', tag + ' tier')
    w, dp = x1 - x0 - 2 * inset, y1 - y0 - 2 * inset
    for fx, fy, sz in ((.25, .35, .18), (.65, .6, .14)):
        bw = max(24, int(min(w, dp) * sz))
        bx, by = x0 + inset + int(w * fx) - bw // 2, y0 + inset + int(dp * fy) - bw // 2
        box(bx, by, h, bx + bw, by + bw, h + int(bw * .7), 'bm_rock', tag + ' boulder')


def gateway(axis, c0, c1, a, b, gap, h=WALL_H, texture=MID, tag='lane wall', leaves='+'):
    """A wall run with one doorway: a timber header over it and, optionally,
    two door leaves swung open on the '+' or '-' side (None for no leaves).

    axis 'x': the wall runs along X from a to b, occupying y c0..c1.
    axis 'y': the wall runs along Y from a to b, occupying x c0..c1.
    gap is (g0, g1) along the run, open from the floor to 128.
    """
    g0, g1 = gap
    def seg(p, q, z0, z1, tex, t):
        if axis == 'x':
            box(p, c0, z0, q, c1, z1, tex, t)
        else:
            box(c0, p, z0, c1, q, z1, tex, t)
    seg(a, g0, 0, h, texture, tag)
    seg(g1, b, 0, h, texture, tag)
    seg(g0, g1, 128, h, 'bm_wood', 'doorway header')
    if leaves:
        n0, n1 = (c1, c1 + 56) if leaves == '+' else (c0 - 56, c0)
        for p in (g0 - 8, g1):
            if axis == 'x':
                box(p, n0, 0, p + 8, n1, 124, 'bm_door', 'door leaf')
            else:
                box(n0, p, 0, n1, p + 8, 124, 'bm_door', 'door leaf')


def lanes():
    """Walls that turn the open desert into three routes joined at chokepoints.

    T side:  Long A (west canyon, through Long Doors), Mid (through Mid Doors,
             splitting to Short A via the law office and to the B alley), and
             East (fuel stop, through the Scrapyard Gate, to the laundry's east
             door or the blockhouse ladder).
    CT side: a fenced gate onto the A yard, and the pocket west of the laundry
             leading to its west and north doors.
    Ground that walls would otherwise seal off is filled with rock instead of
    being left as unreachable empty space.
    """
    # T spawn plaza: three exits - west (Long, in canyon rock), north into mid,
    # east (the east route, in corrugated metal).
    lane_wall(-672, -1664, -640, -1250, texture=LONG); lane_wall(-672, -1090, -640, -932, texture=LONG)
    lane_wall(640, -1664, 672, -1350, texture=EAST); lane_wall(640, -1190, 672, -932, texture=EAST)
    lane_wall(336, -964, 672, -932, texture=EAST)
    cliff(-1040, -932, -336, -608, 224)                               # behind the motel
    # Mid: side walls from the plaza to Hermanos, open only at the two porches
    # and the B alley, with a doorway halfway that breaks the spawn-to-CT sightline.
    lane_wall(-336, -932, -304, -480); lane_wall(-336, -304, -304, 208); lane_wall(-336, 384, -304, 784)
    lane_wall(304, -932, 336, 176, sides={'+x': EAST})                # east face: the field
    lane_wall(304, 304, 336, 784, sides={'+x': CTW})                  # east face: the CT pocket
    lane_wall(336, -512, 400, 144, h=176, texture=EAST, sides={'+y': MID})   # beside the utility shed
    # Leaves on the T side: the pickup parked just north is the CT cover here.
    gateway('x', -176, -144, -304, 304, (32, 160), leaves='-')     # Mid Doors
    lane_wall(-528, 480, -336, 512)                                # closes the porch strip at Short A
    # Splits the porch strip between the motel and the law office, level with Mid
    # Doors - otherwise the porches are a side path round them.
    lane_wall(-528, -192, -336, -160)
    # Long: an inner wall behind the motel row, rock narrowing the far end, and
    # Long Doors across the canyon.
    lane_wall(-1040, -192, -1008, 80, texture=LONG, sides={'+x': MID})
    cliff(-1232, -64, -1008, 496, 256)
    gateway('x', -64, -32, -1712, -1232, (-1500, -1372), texture=LONG)   # Long Doors
    # B alley: shut off from the CT pocket to the north and the scrapyard to the east.
    lane_wall(336, 320, 576, 352, sides={'+y': CTW})
    lane_wall(848, 128, 1120, 160, texture=EAST, sides={'+y': MID})
    lane_wall(1056, 160, 1120, 320, texture=EAST, sides={'-x': MID})   # up to the blockhouse
    # East: the Scrapyard Gate behind the fuel canopy, and the strip up the
    # laundry's east side closed off before it reaches CT spawn.
    gateway('x', -640, -608, 832, 1120, (928, 1056), texture=EAST)   # Scrapyard Gate
    lane_wall(864, -608, 920, -512, texture=EAST)                   # up to the gate's door leaf
    lane_wall(1552, -656, 1712, -608, texture=EAST)
    cliff(1552, 640, 1712, 1152, 224)
    # CT: a fence across the top of the A yard with one gate.
    gateway('x', 1248, 1280, -1712, -448, (-1028, -900), h=144, texture=CTW,
            tag='fence wall', leaves=None)
    lane_wall(-448, 1184, -416, 1280, h=144, texture=CTW, tag='fence wall')


def landmarks():
    """Tall markers that read over the lane walls, one per part of the map.

    The walls are 192 high, so without these a player in a lane sees nothing
    but wall. Each marker stands on something unreachable - the mesa, the
    laundry roof, the top of a wall - so none of them changes the play space.
    """
    # A: a water tower on the mesa between Long and Short A, banded in A orange.
    cx, cy, top = -1120, 216, 256
    for dx in (-48, 48):
        for dy in (-48, 48):
            box(cx + dx - 6, cy + dy - 6, top, cx + dx + 6, cy + dy + 6, top + 264, 'bm_rust', 'water tower leg')
    cylinder(cx, cy, top + 264, top + 384, 72, 'bm_tower', 'water tower tank', sides=12)
    cylinder(cx, cy, top + 384, top + 396, 78, 'bm_metal', 'water tower roof', sides=12)
    cylinder(cx, cy, top + 396, top + 416, 40, 'bm_metal', 'water tower roof', sides=12)
    # B: a brick smokestack on the laundry roof, with a teal band near the top.
    sx, sy, roof = 1480, 1080, 240
    cylinder(sx, sy, roof, 620, 28, 'bm_brick', 'smokestack', sides=10)
    cylinder(sx, sy, 620, 652, 30, 'bm_blue', 'smokestack band', sides=10)
    cylinder(sx, sy, 652, 700, 28, 'bm_brick', 'smokestack', sides=10)
    cylinder(sx, sy, 700, 712, 32, 'bm_black', 'smokestack cap', sides=10)
    # East route: a fuel-price pylon standing on the plaza's east wall.
    box(648, -1508, WALL_H, 664, -1492, 480, 'bm_rust', 'fuel pylon')
    b = box(648, -1580, 480, 664, -1420, 576, 'bm_metal', 'fuel pylon sign', faces={0: 'bm_fuelsign', 1: 'bm_fuelsign'})
    su, sv = 160 / 256, 96 / 64
    b['faces'][0]['uv'] = [[0, -1, 0, -1420 / su], [0, 0, -1, 576 / sv], su, sv]
    b['faces'][1]['uv'] = [[0, 1, 0, 1580 / su], [0, 0, -1, 576 / sv], su, sv]


def direction_sign(wx, wy, z, facing, site, toward=None, arrow=None, size=64):
    """A painted A / B sign on a wall face, its arrow pointing along the route.

    For '-y' / '+y' faces (wx, wy) is the sign's centre along the wall and the
    wall face's y; for '-x' / '+x' it is the wall face's x and the centre along
    the wall. The arrow is worked out from where `toward` - a point further
    along the route - lies for someone standing in front of the sign reading
    it: ahead (up), left or right. `arrow='d'` marks a way down.
    """
    nx, ny = {'-y': (0, -1), '+y': (0, 1), '-x': (-1, 0), '+x': (1, 0)}[facing]
    if arrow is None:
        fx, fy = -nx, -ny                  # the reader looks into the wall
        rx, ry = fy, -fx                   # and this is their right
        tx, ty = toward[0] - wx, toward[1] - wy
        a = math.degrees(math.atan2(tx * rx + ty * ry, tx * fx + ty * fy))
        arrow = 'u' if abs(a) < 35 else ('r' if a > 0 else 'l')
    tex = f'bm_dir_{site.lower()}_{arrow}'
    if facing in ('-y', '+y'):
        wall_art(wx - size // 2, wy - 4 if facing == '-y' else wy + 4, z, size, size, tex, facing, 'direction sign')
    else:
        wall_art(wx - 4 if facing == '-x' else wx + 4, wy - size // 2, z, size, size, tex, facing, 'direction sign')
    return arrow


def signs():
    """Direction signs at every junction and chokepoint, T side and CT side."""
    S = direction_sign
    # T spawn: the three exits.
    S(-640, -1028, 72, '+x', 'A', toward=(-700, -1170))      # west exit -> Long
    S(640, -1128, 72, '-x', 'B', toward=(720, -1270))        # east exit -> east route
    S(-304, -860, 72, '+x', 'A', toward=(0, -160))           # into mid
    S(304, -860, 72, '-x', 'B', toward=(96, -160))
    # Long.
    S(-1040, -848, 72, '-x', 'A', toward=(-1436, -120))      # outside Long, by the motel
    S(-1560, -64, 72, '-y', 'A', toward=(-1436, 300))        # Long Doors
    # Mid Doors, then the split past them.
    S(-120, -176, 72, '-y', 'A', toward=(96, 200))
    S(-40, -176, 72, '-y', 'B', toward=(96, 200))
    S(-304, 432, 72, '+x', 'A', toward=(-420, 296))          # Short A, via the law office
    S(304, 352, 72, '-x', 'B', toward=(340, 240))            # the B alley
    S(1080, 320, 64, '-y', 'B', arrow='d')                   # the laundry's south door
    # East route.
    S(1120, -1032, 124, '-x', 'B', toward=(992, -620), size=48)   # at the fuel shop
    S(880, -640, 72, '-y', 'B', toward=(992, -400))          # Scrapyard Gate
    S(992, -432, 72, '-y', 'B', toward=(1200, -300))         # round the container
    S(1552, 592, 64, '+x', 'B', arrow='d')                   # the laundry's east door
    # CT side.
    S(-268, 1184, 72, '+y', 'A', toward=(-836, 1264))        # at CT spawn
    S(268, 1184, 72, '+y', 'B', toward=(1144, 1152))
    S(-1096, 1280, 64, '+y', 'A', toward=(-964, 1000))       # CT Gate
    S(-416, 1128, 64, '+x', 'A', toward=(-500, 1016))        # inside Hermanos, at its west door
    S(872, 1136, 72, '-y', 'B', arrow='d')                   # laundry, by the lift
    S(1296, 1136, 64, '-y', 'B', arrow='d')                  # laundry, over the CT hatch
    S(592, 892, 104, '+x', 'B', arrow='d')                   # laundry, by the west door


def wreck(x, y, along='x'):
    """A stripped car on its rims: standing cover, 84 units at the cabin."""
    L, W = 176, 80
    x1, y1 = (x + L, y + W) if along == 'x' else (x + W, y + L)
    box(x, y, 0, x1, y1, 44, 'bm_rust', 'car wreck')
    if along == 'x':
        box(x + 48, y + 6, 44, x + 128, y + 74, 84, 'bm_rust', 'car wreck cabin', faces={2: 'bm_glass', 3: 'bm_glass'})
    else:
        box(x + 6, y + 48, 44, x + 74, y + 128, 84, 'bm_rust', 'car wreck cabin', faces={0: 'bm_glass', 1: 'bm_glass'})


def barrier(x0, y0, x1, y1):
    """Concrete jersey barrier: crouch cover."""
    box(x0, y0, 0, x1, y1, 40, 'bm_concrete', 'barrier')


def cover():
    """Cover for the ground the lanes leave open, so no stretch is a bare field."""
    # Outside T spawn and on the way to Long.
    wreck(-940, -1200)
    box(-1600, -420, 0, -1480, -300, 144, 'bm_rock', 'canyon cover')
    # Long, before it opens onto A.
    crate(-1296, 400, size=64); crate(-1288, 408, z=64, size=48)   # against the rock
    wreck(-1400, 150, along='y')       # mid-Long: breaks the one long run from the doors
    # A yard: a tool shed facing Short A, tyre stacks by the CT gate, and a
    # ladder onto the RV roof for a high position that is exposed from both entrances.
    box(-600, 620, 0, -464, 748, 112, 'bm_wood', 'A shed')
    box(-608, 612, 112, -456, 756, 124, 'bm_roof', 'A shed roof')
    for tx, ty in [(-1000, 1150), (-956, 1150)]:
        cylinder(tx, ty, 0, 32, 22, 'bm_black', 'tyre stack'); cylinder(tx, ty, 32, 64, 22, 'bm_black', 'tyre stack')
        clip(tx - 22, ty - 22, 0, tx + 22, ty + 22, 64)
    eid = brush_entity('func_ladder')
    box(-920, 916, 0, -904, 972, 196, 'AAATRIGGER', 'RV roof ladder', eid, False)
    for yy in (916, 968):
        box(-920, yy, 0, -914, yy + 4, 192, 'bm_rust', 'ladder rail')   # against the RV's back
    for z in range(16, 192, 16):
        box(-920, 920, z, -914, 968, z + 4, 'bm_rust', 'ladder rung')
    # Mid, T side of the doors.
    barrier(-240, -620, -112, -596); barrier(96, -400, 224, -376)
    # The B alley: a dumpster and a crate stack.
    box(700, 144, 0, 796, 192, 56, 'bm_teal', 'dumpster')             # against the utility shed
    box(696, 144, 56, 800, 196, 62, 'bm_black', 'dumpster lid')
    crate(480, 200, size=64)
    # The field south of the utility shed: two shipping containers in an L.
    # Set into the corner of the mid wall and the plaza wall, so no strip is left behind them.
    box(336, -932, 0, 592, -836, 112, 'bm_metal', 'shipping container')
    box(336, -836, 0, 432, -676, 112, 'bm_rust', 'shipping container')
    # A loading dock fills the dead-end bay between the utility shed and the Scrapyard Gate.
    box(640, -608, 0, 864, -512, 64, 'bm_concrete', 'loading dock')
    # Outside the laundry's east side: a transformer cabinet.
    box(1400, 240, 0, 1480, 320, 96, 'bm_metal', 'transformer')      # against the laundry
    # CT exits.
    barrier(-600, 1328, -472, 1352); barrier(472, 1328, 600, 1352)   # 48 clear of the fence


# ambient_generic radius flags. GoldSrc fades a sound linearly to nothing at
# 1000 / attenuation, so these fall silent at roughly 500, 800 and 1250 units.
SMALL, MEDIUM, LARGE = 2, 4, 8

# One-shot clips the map's owner supplies rather than the generator: a PCM WAV
# at source/sounds/<name>_source.wav. The generator cuts `seconds` from where
# the sound starts (plus `start`) and gives each its own one-shot, play-
# everywhere ambient_generic named `event`. With no file, the map simply has no
# such sound.
#   death   - named game_playerdie, which CS fires whenever any player dies.
#             This works on any server, with or without the plugin.
#   knife   - no map event can tell which weapon made a kill, so the AMX Mod X
#   grenade   plugin tools/amxx/bluemesa_knife.sma fires these by name. Where
#             the plugin runs, it also takes over game_playerdie, so each
#             death plays exactly one sound: knife, grenade, or death.
CLIPS = {
    # start 0: the clip's opening moment - option A of the four exported, picked by ear.
    'death':   dict(event='game_playerdie', seconds=1.2, start=0.0, volume=8),
    'knife':   dict(event='bm_snd_knife', seconds=1.2, start=3.53, volume=10),   # new clip, option D
    'grenade': dict(event='bm_snd_grenade', seconds=2.0, start=0.0, volume=10),
}


def clip_source(name):
    return SOURCE / 'sounds' / f'{name}_source.wav'


def ambient(origin, sound, volume, radius=SMALL, **keys):
    """A looping sound. Keys match Valve's own CS maps."""
    return point('ambient_generic', origin, message=sound, health=volume,
                 pitch=100, pitchstart=100, spawnflags=radius, **keys)


def soundscape():
    """Stock CS 1.6 / Half-Life sounds, plus the one track the map ships itself.

    Every file has loop cue points - GoldSrc plays a WAV without them once and
    stops. Sound in GoldSrc ignores walls, so the mix is done with distance:
    the underground sources are small-radius and quiet, reaching the laundry
    floor above only as a faint hum, and the surface wind sits at least 800
    units from the superlab so the room below stays sealed-off and still.
    Volumes are kept low near both bomb sites so footsteps stay readable.
    """
    # The superlab: reactor drone, one ceiling extractor, the control-room monitors.
    ambient((1250, 900, -200), 'ambience/labdrone2.wav', 3)
    ambient((880, 944, -150), 'fans/fan4.wav', 3)
    ambient((680, 560, -220), 'ambience/computalk1.wav', 5)
    # Water working down the outside access shaft and into its tunnel.
    ambient((1216, 250, -140), 'ambience/drips.wav', 5)
    # The laundry floor: the one washer that is still plumbed in.
    ambient((672, 896, 110), 'ambience/industrial1.wav', 3)
    # Desert wind over the open ground, clear of the laundry and the lab.
    for origin, sound, volume in [((-1400, -900, 256), 'ambience/wind2.wav', 4),
                                  ((-1400, 450, 256), 'ambience/wind1.wav', 2),
                                  ((-500, -1300, 256), 'ambience/wind2.wav', 4),
                                  ((0, -150, 320), 'ambience/wind2.wav', 3),
                                  ((-500, 1400, 256), 'ambience/wind1.wav', 2),
                                  ((1100, -1350, 256), 'ambience/wind2.wav', 4),
                                  ((1550, -350, 256), 'ambience/wind2.wav', 3)]:
        ambient(origin, sound, volume, MEDIUM)
    # Buzzing signs: the Hermanos rooftop sign and the motel plaque.
    ambient((208, 1000, 392), 'ambience/lv_neon.wav', 5)
    ambient((-480, -400, 200), 'ambience/lv_neon.wav', 5)
    # Flies around the scrapyard container, and the RV's generator ticking over.
    ambient((1088, -470, 40), 'ambience/flies.wav', 6)
    ambient((-900, 964, 40), 'ambience/tankidle1.wav', 2)
    # The RV radio: the map's own original track, which the counter-top boombox
    # switches off when it is shot. Small radius, so it colours the RV and the
    # plant zone beside it without carrying across the whole A yard.
    ambient((-1280, 1016, 152), f'{SOUND_DIR}/mesa_radio.wav', 6, targetname='rv_radio')
    # The owner's one-shot clips (see CLIPS). Play-everywhere + start silent +
    # not looped: each firing plays the clip once to the whole server, and a
    # firing while it is still playing restarts it rather than stacking.
    for i, (name, c) in enumerate(CLIPS.items()):
        if clip_source(name).exists():
            ambient((0, 32 * i, 400), f'{SOUND_DIR}/{name}.wav', c['volume'], 1 | 16 | 32,
                    targetname=c['event'])


def make_map():
    point('worldspawn',None,mapversion='220',wad='bluemesa.wad',skyname='bmesa',
          message='Blue Mesa - a map by YAMAN',maxrange='4096')
    # Six closed structural faces; no entity needs to seal the world. The ground
    # slab is pierced by the three descents into the superlab.
    slab_with_holes(-1792,-1728,-64,1792,1728,0,DESCENT_HOLES,'bm_sand','ground')
    box(-1856,-1792,-64,-1792,1792,832,'sky','sky enclosure')
    box(1792,-1792,-64,1856,1792,832,'sky','sky enclosure')
    box(-1792,-1792,-64,1792,-1728,832,'sky','sky enclosure')
    box(-1792,1728,-64,1792,1792,832,'sky','sky enclosure')
    box(-1792,-1728,768,1792,1728,832,'sky','sky enclosure')
    # Sandstone boundaries and varied capstones.
    box(-1792,-1728,0,-1712,1728,192,'bm_rock','boundary')
    box(1712,-1728,0,1792,1728,192,'bm_rock','boundary')
    box(-1712,-1728,0,1712,-1664,160,'bm_rock','boundary')
    box(-1712,1664,0,1712,1728,192,'bm_rock','boundary')
    for i,y in enumerate(range(-1664,1664,384)):
        box(-1792,y,192,-1736,y+256,256+32*(i%3),'bm_rock','boundary crest')
        box(1744,y,192,1792,y+224,240+24*(i%4),'bm_rock','boundary crest')
    # Floor overlays are two units high, comfortably below step height.
    box(-448,-1664,0,448,-1056,2,'bm_asphalt','road')
    box(-288,-1056,0,288,784,2,'bm_asphalt','road')
    box(-640,1200,0,640,1664,2,'bm_asphalt','road')
    box(576,-1120,0,1088,-608,2,'bm_concrete','forecourt')
    for y in range(-1024,688,256):box(-5,y,2,5,y+112,3,'bm_hazard','road markings')
    # Narrow enough to leave a 128-unit way into mid on each side.
    box(-176,-1072,0,176,-928,160,'bm_stucco','T spawn screen')
    plaque(-160,-1076,60,320,80,'bm_credit')   # the first thing Ts see each round
    # Team starts: 16 per side, feet on the raised asphalt.
    for team,ys,angle,classname in [
        ('T',[-1536,-1464,-1392,-1320],90,'info_player_deathmatch'),
        ('CT',[1344,1416,1488,1560],270,'info_player_start')]:
        for y in ys:
            for x in [-108,-36,36,108]:point(classname,(x,y,38),angle=angle)
        eid=brush_entity('func_buyzone',team=1 if team=='T' else 2)
        by=(-1600,-1184) if team=='T' else (1264,1632)
        box(-400,by[0],0,400,by[1],128,'AAATRIGGER',team+' buy zone',eid,False)
    point('info_map_parameters',None,buying='0',bombradius='500')
    # West canyon baffles prevent a single end-to-end lane.
    box(-1712,-832,0,-1424,-512,168,'bm_rock','canyon cover')
    box(-1360,-304,0,-1088,-64,176,'bm_rock','canyon cover')   # flush to Long Doors' wall
    box(-1712,96,0,-1464,352,208,'bm_rock','canyon cover')
    # Down to Long Doors' wall, stopping at its west door leaf so the doorway
    # keeps its full width - this closes the nook that was behind the doors.
    box(-1712,-32,0,-1508,96,208,'bm_rock','canyon cover')
    crate(-1432,-752)
    # The residence: a pass-through landmark on the Terrorist side of the west lane.
    building(-1664,-1424,-1168,-976,160,'bm_stucco','residence',
             {'south':[(-1420,-1300,112)],'east':[(-1204,-1084,112)]},
             windows={'south':[(-1620,-1500)],'east':[(-1370,-1280)],'north':[(-1560,-1440)]},
             roof='bm_shingle',light='244 214 156 260')
    box(-1648,-1408,0,-1420,-992,2,'bm_tile','residence kitchen floor')
    box(-1420,-1408,0,-1184,-992,2,'bm_carpet','residence living floor')
    wall_art(-1636,-1428,0,128,112,'bm_garage','-y','garage door')
    # Kitchen along the west wall, laundry nook against the back wall.
    furnish(-1648,-1352,2,-1560,-1180,44,'bm_wood','bm_cream','kitchen counter')
    box(-1648,-1180,2,-1568,-1080,124,'bm_fridge','kitchen fridge')
    for wx in (-1392,-1288):box(wx,-1072,2,wx+104,-992,90,'bm_washer','residence laundry')
    # Living area.
    box(-1288,-1408,2,-1184,-1304,40,'bm_teal','residence sofa')
    box(-1288,-1408,40,-1184,-1380,76,'bm_teal','sofa back')
    furnish(-1300,-1250,2,-1240,-1190,40,'bm_wood','bm_panel','coffee table')
    furnish(-1400,-1128,2,-1240,-1040,44,'bm_wood','bm_cream','dining table')
    for px,pt in [(-1400,'bm_photo1'),(-1320,'bm_photo2'),(-1240,'bm_photo3')]:
        wall_art(px,-996,96,56,56,pt,'-y','family portrait')
    wall_art(-1490,-1404,80,64,64,'bm_hat','+y','garage poster')
    wall_art(-1184,-1024,76,64,64,'bm_missing','-x','hallway flyer')
    # Carport, driveway and mailbox on the approach side.
    box(-1168,-1330,140,-1000,-1080,156,'bm_teal','carport roof')
    for cy in (-1320,-1104):box(-1016,cy,0,-1000,cy+16,140,'bm_wood','carport post')
    box(-1168,-1330,0,-1000,-1080,2,'bm_asphalt','residence driveway')
    box(-1080,-1240,0,-1064,-1224,44,'bm_wood','mailbox post')
    box(-1092,-1248,44,-1052,-1216,68,'bm_metal','mailbox')
    wall_art(-1088,-1252,48,32,16,'bm_housenum','-y','house number')
    # Above-ground pool behind the house.
    box(-1560,-1600,0,-1320,-1440,16,'bm_concrete','pool surround')
    # Rock fills the dead-end corner beside the pool.
    cliff(-1712,-1664,-1560,-1424,176)
    box(-1544,-1584,16,-1336,-1456,20,'bm_pool','pool water')
    point('light',(-1300,-1200,132),_light='246 220 168 180')
    point('light',(-1120,-1200,132),_light='238 206 150 140')
    # Motel row: room one is still rented out, room two is the strip-mall law office.
    # The motel connects mid to outside Long; the law office is Short A - in from
    # the mid porch, out of its north door onto the A yard. Its canyon door is
    # bricked up, or Long and Short would join behind the row.
    for y0,y1,d0 in [(-608,-192,-464),(80,496,224)]:
        law = y0 > 0
        building(-1008,y0,-528,y1,152,'bm_stucco','law office' if law else 'motel',
                 {'east':[(d0,d0+144,112)],'north':[(-880,-752,112)]} if law else
                 {'east':[(d0,d0+144,112)],'west':[(d0+16,d0+160,112)]},
                 windows={'east':[(392,464)]} if law else {'west':[(-560,-464)]},
                 glass='bm_saul_win' if law else 'bm_window',
                 light='252 246 216 300' if law else '238 214 158 250')
        box(-520,y0,140,-328,y1,156,'bm_teal','motel porch roof')
        for py in (y0,y1-16):box(-352,py,0,-336,py+16,140,'bm_wood','porch post')
        if law:
            box(-992,96,0,-544,480,2,'bm_carpet','law office floor')
            box(-992,96,2,-984,480,152,'bm_law_wall','law office panelling')
            furnish(-924,240,0,-724,344,48,'bm_wood','bm_panel','law desk')
            for cy in (196,368):box(-708,cy,0,-652,cy+56,40,'bm_booth','law chair')
            for fy in (320,400):box(-992,fy,2,-912,fy+80,64,'bm_metal','filing cabinet')
            wall_art(-980,196,76,120,68,'bm_diploma','+x','diploma wall')
            wall_art(-980,352,80,64,64,'bm_photo3','+x','office portrait')
            wall_art(-548,128,72,72,72,'bm_hat','-x','office poster')
            # Rooftop inflatable, visible over the motel roofline from middle.
            cylinder(-820,300,168,244,20,'bm_teal','inflatable figure')
            cylinder(-820,300,244,268,12,'bm_cream','inflatable figure')
            box(-806,296,236,-790,308,300,'bm_cream','inflatable arm')
        else:
            box(-992,y0+16,0,-816,y0+112,32,'bm_wood','motel bed base')
            box(-992,y0+16,32,-816,y0+112,42,'bm_bed','motel bed')
            box(-992,y0+28,42,-948,y0+98,48,'bm_cream','pillow')
            box(-672,y1-80,0,-544,y1-16,48,'bm_wood','motel desk')
            box(-760,y0+16,0,-704,y0+72,40,'bm_wood','motel chair')
            box(-992,y1-104,2,-920,y1-16,152,'bm_panel','motel closet')
            wall_art(-880,y1-20,76,64,64,'bm_photo2','-y','motel print')
            wall_art(-548,y0+56,72,56,72,'bm_missing','-x','motel flyer')
    # The porch strip under the porch roofs measured nearly black (8/255).
    for ly in (-500,-300,160,380):
        point('light',(-436,ly,120),_light='240 214 160 150')
    # The motel's south face is now against rock, so its sign faces mid instead.
    wall_art(-520,-560,168,320,64,'bm_motel','+x','motel sign')
    box(-1032,-96,0,-992,-64,224,'bm_rust','motel signpost')
    plaque(-1200,-98,180,384,96,'bm_saul_ad')
    # Eastern utility block masks the lab approach from middle.
    box(400,-512,0,864,144,176,'bm_metal','utility shed')
    box(392,-520,176,872,152,192,'bm_roof','utility shed roof')
    plaque(464,-526,104,320,64,'bm_rvsign')
    # Middle cover: old pickup silhouette and a staggered barrier.
    box(-160,36,16,128,188,72,'bm_rust','pickup bed')
    box(-160,188,16,128,292,80,'bm_teal','pickup cab')
    box(-144,204,80,112,276,128,'bm_glass','pickup windows')
    box(-160,188,128,128,292,136,'bm_teal','pickup roof')
    for x in [-172,116]:
        for y in [60,228]:box(x,y,0,x+24,y+40,40,'bm_black','pickup tire')
    box(-208,400,0,64,432,104,'bm_concrete','mid barricade')
    crate(144,-704,size=72)
    # Gas station and convenience shop.
    building(1120,-1136,1552,-640,176,'bm_stucco','fuel shop',{'west':[(-976,-816,112)]})
    # Sliding shop door: opens toward the north and returns automatically.
    eid=brush_entity('func_door',angle='90',speed='100',wait='3',lip='8',movesnd='2')
    box(1120,-976,0,1136,-816,112,'bm_door','sliding shop door',eid)
    plaque(1152,-1142,104,352,64,'bm_fuelsign')
    furnish(1400,-832,0,1512,-656,48,'bm_wood','bm_cream','shop counter')
    box(1512,-832,0,1536,-656,96,'bm_panel','shop shelving')
    box(1136,-720,0,1216,-656,124,'bm_fridge','shop cooler')
    wall_art(1376,-660,104,128,32,'bm_fuelsign','-y','shop price board')
    wall_art(1300,-660,44,56,112,'bm_menu','-y','shop menu')
    wall_art(1140,-1080,80,48,48,'bm_missing','+x','shop flyer')
    # Vending machine under the canopy, shootable.
    eid=brush_entity('func_breakable',material='1',health='40',spawnflags='0')
    box(1088,-1080,0,1120,-984,120,'bm_vending','vending machine',eid)
    box(576,-1104,208,1056,-608,224,'bm_cream','fuel canopy roof')
    box(576,-1106,184,1056,-1088,208,'bm_rust','fuel fascia')
    plaque(608,-1112,186,416,36,'bm_fuelsign')
    # The north posts stand back from the canopy edge, clear of the Scrapyard Gate.
    for x in [624,1008]:                  # the west posts flush to the plaza wall
        for y in [-1064,-720]:box(x,y,0,x+16,y+16,208,'bm_rust','canopy post')
    for y in [-992,-752]:
        box(736,y,0,824,y+72,12,'bm_concrete','pump island')
        b=box(752,y+8,12,808,y+64,100,'bm_pump','fuel pump')
        for face in b['faces']:
            if abs(face['normal'][2])<.1:
                axis=1 if abs(face['normal'][0])>.5 else 0
                lo=b['min'][axis];hi=b['max'][axis]
                u=[0,0,0,-lo/((hi-lo)/128)];u[axis]=1
                face['uv']=[u,[0,0,-1,100/((100-12)/128)],(hi-lo)/128,(100-12)/128]
    point('light',(800,-856,186),_light='236 215 150 180')
    # Scrapyard dogleg and an accessible maintenance platform.
    box(864,-432,0,1120,-176,120,'bm_metal','scrapyard container')   # flush to the shed, clear of the blockhouse door
    box(864,-432,120,1120,-176,128,'bm_rust','container lid')
    crate(1312,-576,size=96);crate(1392,-480,size=80)
    cylinder(1520,-300,0,88,40,'bm_blue','scrapyard drum')
    clip(1480,-340,0,1560,-260,88)
    box(1440,-144,112,1632,144,128,'bm_wood','maintenance platform')
    for x in [1456,1600]:
        for y in [-128,112]:box(x,y,0,x+16,y+16,112,'bm_rust','platform support')
    for y in [-144,136]:box(1440,y,128,1632,y+8,164,'bm_rust','platform rail')
    box(1432,-144,128,1440,144,164,'bm_rust','platform rail')
    for ya,yb in [(-144,-48),(48,144)]:box(1624,ya,128,1632,yb,164,'bm_rust','platform rail')
    eid=brush_entity('func_ladder')
    box(1632,-32,0,1640,32,152,'AAATRIGGER','platform ladder',eid,False)
    for y in [-32,28]:box(1632,y,0,1638,y+4,152,'bm_rust','ladder rail')
    for z in range(16,144,16):box(1632,-28,z,1638,28,z+4,'bm_rust','ladder rung')
    # Site B, a functional industrial interior.
    # South door: the T main from the B alley, with the stair straight ahead.
    # East door: the T flank from the scrapyard. West and north: CT entrances.
    building(576,320,1552,1152,224,'bm_metal','laundry lab',
             {'south':[(864,1040,128)],'west':[(656,832,128)],'north':[(1056,1232,128)],
              'east':[(400,528,128)]})
    # The floor is pierced by the elevator bay and the stairwell down to the lab.
    slab_with_holes(592,336,0,1536,1136,2,[HOLE_ELEVATOR,HOLE_STAIRS,HOLE_HATCH],'bm_tile','lab floor')
    # The CT hatch: a hazard kerb low enough to step over, so nobody falls in by
    # accident, running round to the north wall.
    hx0,hy0,hx1,hy1=HOLE_HATCH
    for rx0,ry0,rx1,ry1 in [(hx0-16,hy0-16,hx1+16,hy0),(hx0-16,hy0,hx0,1136),(hx1,hy0,hx1+16,1136),(hx0,hy1,hx1,1136)]:
        box(rx0,ry0,2,rx1,ry1,18,'bm_hazard','hatch kerb')
    plaque(720,314,150,624,64,'bm_laundry')
    # Only the south washer is still plumbed in; the north one is the lift car.
    # It stands a clear 32 south of the lift shaft.
    b=box(592,848,2,720,944,98,'bm_washer','industrial washers')
    b['faces'][1]['uv']=[[0,1,0,-848/(96/128)],[0,0,-1,98/(96/128)],96/128,96/128]
    for x,y in [(864,944),(1264,656)]:
        cylinder(x,y,2,114,48,'bm_blue','lab tank')
        clip(x-48,y-48,2,x+48,y+48,114)
        cylinder(x,y,114,122,40,'bm_metal','tank top')
        cylinder(x,y,122,144,10,'bm_metal','tank vent')
    box(1408,816,2,1536,1056,54,'bm_metal','lab workbench')
    box(1400,808,54,1536,1064,62,'bm_cream','workbench top')
    eid=brush_entity('func_breakable',material='0',health='15',rendermode='2',renderamt='140',rendercolor='150 190 190')
    cylinder(1480,864,62,100,18,'bm_glass','glass vessel',entity=eid)
    cylinder(1464,984,62,108,20,'bm_metal','lab canister')
    box(784,528,2,944,600,74,'bm_crate','B entry cover')   # flush to the stair rail
    box(640,1100,184,1456,1116,200,'bm_hazard','overhead pipe')
    box(1440,384,176,1456,1116,192,'bm_hazard','overhead pipe')
    point('light',(864,768,192),_light='165 219 218 220')
    point('light',(1320,992,192),_light='189 216 193 190')
    # The investigation board and safety notices give the lab walls something to read.
    wall_art(1536,620,72,128,128,'bm_dea','-x','investigation board')
    wall_art(1060,340,88,64,64,'bm_diploma','+y','lab safety notice')
    wall_art(960,1132,88,64,64,'bm_diploma','-y','lab safety notice')
    # Two more fluorescent runs so the interior is not lit by a single source.
    point('light',(700,480,196),_light='196 220 214 200')
    point('light',(1180,420,196),_light='196 220 214 190')
    # The objective is no longer on this floor; the laundry is now the way in.
    superlab()
    # Hermanos chicken stop: the CT-side landmark, still forcing left / right exits.
    building(-432,784,432,1184,208,'bm_stucco','hermanos',
             {'south':[(-80,80,128)],'west':[(944,1088,128)],'east':[(944,1088,128)]},
             windows={'south':[(-368,-208),(208,368)],'east':[(830,910)]},
             light='250 240 206 320',
             # The front windows look straight down mid: CTs can shoot them out
             # and hold mid from inside, an answer to Ts taking Mid Doors first.
             breakable=('south',))
    plaque(-208,778,144,416,64,'bm_pollos')
    # The author's credit on the back wall, facing the CTs as they spawn.
    wall_art(-160,1188,80,320,80,'bm_credit','+y','CT spawn credit board')
    box(-416,800,0,416,1168,2,'bm_checker','hermanos floor')
    # Service counter, fry line and cooler along the back wall.
    furnish(-320,1064,0,-96,1168,52,'bm_wood','bm_cream','order counter')
    box(-96,1080,0,0,1168,88,'bm_fryer','fry line')
    box(256,1096,0,416,1168,104,'bm_fridge','drinks cooler')
    for i,mx in enumerate((-300,-220,-140)):
        wall_art(mx,1164,72,64,128,'bm_menu','-y','menu board')
    wall_art(-412,820,64,96,64,'bm_diploma','+x','health notice')   # clear of the west door
    wall_art(120,1164,60,72,72,'bm_missing','-y','counter flyer')
    # Two booths under the front windows, clipped as solid blocks so players cannot
    # wedge into the seats. They stand 64 in from the side walls and stop short of
    # the side doors, which leaves an aisle from each side door to the front door -
    # Hermanos is a connector between mid, the A yard and the CT pocket.
    for bx in (-352,200):
        for by in (848,):                 # 48 from the front wall: room to hold the windows
            box(bx,by,0,bx+152,by+28,40,'bm_booth','booth bench')
            box(bx,by+84,0,bx+152,by+112,40,'bm_booth','booth bench')
            box(bx,by,40,bx+152,by+8,76,'bm_booth','booth back')
            box(bx,by+104,40,bx+152,by+112,76,'bm_booth','booth back')
            furnish(bx+20,by+36,0,bx+132,by+76,42,'bm_metal','bm_cream','booth table')
            clip(bx,by,0,bx+152,by+112,76)
    # Rooftop sign, readable from middle and from the CT road.
    box(96,1008,224,320,1048,232,'bm_rust','rooftop sign base')
    # Raised on tall posts so it reads over the mid walls as a landmark.
    for sx in (100,308):box(sx,1016,232,sx+12,1040,448,'bm_rust','rooftop sign post')
    wall_art(112,1020,344,192,96,'bm_pollos_lg','-y','rooftop sign')
    wall_art(112,1028,344,192,96,'bm_pollos_lg','+y','rooftop sign')
    for bx in (-176,144):box(bx,720,0,bx+16,736,44,'bm_rust','forecourt bollard')
    # A yard: dusty RV compound and modest defusal cover.
    floor_decal(-1384,576,240,'bm_sitea')
    box(-1648,1184,0,-1424,1248,104,'bm_wood','A rear cover')   # flush to the fence
    crate(-768,736,size=96);crate(-680,832,size=72)
    cylinder(-1568,736,0,80,32,'bm_blue','A drum')
    cylinder(-1504,712,0,80,32,'bm_rust','A drum')
    clip(-1600,680,0,-1472,768,80)
    # RV has enterable interior, real window openings and a 16-unit stair.
    box(-1416,864,48,-920,1064,64,'bm_black','RV floor')
    # Solid underneath: the floor is 48 up, and a crouching player fits in 36,
    # so an open underside was a crawl-space inside the bomb zone.
    box(-1420,864,0,-920,1064,48,'bm_black','RV skirt')
    box(-1416,864,64,-1400,1064,176,'bm_cream','RV front')
    box(-936,864,64,-920,1064,176,'bm_cream','RV back')
    box(-1400,1048,64,-936,1064,100,'bm_rvstripe','RV north wall')
    box(-1400,1048,148,-936,1064,176,'bm_cream','RV north lintel')
    for x0,x1 in [(-1400,-1352),(-1224,-1160),(-1032,-936)]:
        box(x0,1048,100,x1,1064,148,'bm_cream','RV north frame')
    for x0,x1 in [(-1352,-1224),(-1160,-1032)]:
        eid=brush_entity('func_breakable',material='0',health='20',rendermode='2',renderamt='130',rendercolor='110 156 161')
        box(x0,1052,100,x1,1056,148,'bm_glass','RV breakable window',eid)
    box(-1400,864,64,-1120,880,104,'bm_rvstripe','RV south wall')
    box(-1400,864,148,-1120,880,176,'bm_cream','RV south upper frame')
    box(-1400,864,104,-1376,880,148,'bm_cream','RV south window frame')
    box(-1248,864,104,-1120,880,148,'bm_cream','RV south window frame')
    eid=brush_entity('func_breakable',material='0',health='20',rendermode='2',renderamt='130',rendercolor='110 156 161')
    box(-1376,868,104,-1248,872,148,'bm_glass','RV breakable window',eid)
    box(-1016,864,64,-936,880,176,'bm_rvstripe','RV south wall')
    box(-1120,864,168,-1016,880,176,'bm_cream','RV door header')
    box(-1424,856,176,-912,1072,192,'bm_cream','RV roof')
    box(-1240,928,192,-1144,1016,216,'bm_cream','RV roof vent')
    for i in range(4):box(-1120,800+i*16,0,-1016,816+i*16,16*(i+1),'bm_metal','RV stair')
    box(-1384,960,64,-1264,1032,108,'bm_metal','RV counter')
    box(-1392,952,108,-1256,1040,114,'bm_cream','RV counter top')
    # A boombox on the counter plays the map's own track (see make_music.py).
    # Shoot it and the music stops, the way the radio in Valve's cs_italy works:
    # a breakable whose target is the ambient_generic playing the song.
    eid=brush_entity('func_breakable',material='6',health='50',target='rv_radio')
    b=box(-1300,1004,114,-1260,1028,138,'bm_black','RV radio',eid,faces={2:'bm_radio'})
    b['faces'][2]['uv']=[[1,0,0,1300/(40/128)],[0,0,-1,138/(24/64)],40/128,24/64]
    cylinder(-1320,992,114,148,16,'bm_glass','RV vessel')
    box(-992,936,64,-944,1024,96,'bm_bed','RV seat')
    for x in [-1328,-1008]:
        wheel(x,848,876);wheel(x,1052,1080)
    plaque(-1224,858,122,96,24,'bm_rvsign')
    # Windshield, front grille, headlamps and bumper make the vehicle legible.
    b=box(-1420,888,112,-1416,1040,160,'bm_glass','RV windshield')
    b['faces'][0]['uv']=[[0,1,0,-888/(152/128)],[0,0,-1,160/(48/128)],152/128,48/128]
    box(-1432,880,68,-1416,1048,104,'bm_cream','RV nose')
    box(-1436,912,76,-1432,1016,96,'bm_metal','RV grille')
    for yy in [888,1020]:box(-1436,yy,84,-1432,yy+20,100,'bm_cream','RV headlight')
    box(-1440,876,0,-1420,1052,64,'bm_black','RV bumper')   # down to the ground: no slot under the nose
    wall_art(-1444,948,24,32,16,'bm_plate','-x','RV licence plate')
    wall_art(-1396,900,108,48,48,'bm_hat','+x','RV poster')
    wall_art(-936,890,104,40,40,'bm_missing','-x','RV flyer')
    point('light',(-1168,976,160),_light='208 222 167 100')
    for lx in (-1340,-990):            # its corners measured as dark as 7/255
        point('light',(lx,968,150),_light='224 226 196 110')
    eid=brush_entity('func_bomb_target')
    # Tops out below the RV roof (192): planting inside the RV is fine, on its roof is not.
    box(-1648,560,0,-608,1248,160,'AAATRIGGER','A bomb site',eid,False)
    # Lighting is deliberately bright enough for the original renderer.
    point('light_environment',(0,0,608),angles='-55 35 0',pitch='-55',_light='255 222 169 230',_diffuse_light='149 186 190 80')
    point('light',(-1392,-96,240),_light='232 197 143 100')
    point('light',(1344,0,240),_light='232 197 143 100')
    # Route lighting: two roadside poles and the maintenance platform.
    for px,py in [(-304,40),(288,560)]:     # flush to the mid walls
        box(px,py,0,px+16,py+16,192,'bm_rust','light pole')
        box(px-8,py-8,192,px+24,py+24,200,'bm_metal','pole head')
        point('light',(px+8,py+8,186),_light='244 226 176 200')
    point('light',(1536,0,180),_light='236 215 150 150')
    clip(1088,-1080,0,1120,-984,120)
    for cy in (-992,-752):clip(736,cy,0,824,cy+72,100)
    # Signage emits light so the landmarks read at RAD's ambient level.
    point('info_texlights',None,**{'bm_pollos':'900','bm_pollos_lg':'700','bm_menu':'600',
                                   'bm_saul_ad':'500','bm_fuelsign':'600','bm_saul_win':'350'})
    lanes()
    cover()
    landmarks()
    signs()
    soundscape()
    for brush in BRUSHES:
        for face in brush['faces']:
            if face['texture']=='bm_rvstripe' and abs(face['normal'][2])<.1:
                u=[0,1,0,0] if abs(face['normal'][0])>.5 else [1,0,0,0]
                face['uv']=[u,[0,0,-1,176],1,1]


def reveal_exposed_faces():
    """Draw any undrawn face that nothing actually covers.

    wall_art leaves every face but the picture undrawn (NULL), on the promise
    that the plate hangs flat on a wall. Where it doesn't - a sign hanging in the
    air, a sign whose wall has since moved, a plate's 4-unit edges - GoldSrc shows
    the undrawn face as a see-through smear, with players visible through it. So
    each NULL face is probed one unit in front of itself, and any that opens onto
    air gets the plate's backing texture instead.
    """
    tools = {'NULL', 'CLIP', 'AAATRIGGER', 'sky'}
    occ = [b for b in BRUSHES if b['solid']
           and ENTITIES[b['entity']]['keys']['classname'] in ('worldspawn', 'func_wall')
           and any(f['texture'] not in tools for f in b['faces'])]
    mn = np.array([b['min'] for b in occ]); mx = np.array([b['max'] for b in occ])
    planes = [(np.array([f['normal'] for f in b['faces']]),
               np.array([np.dot(f['normal'], f['points'][0]) for f in b['faces']])) for b in occ]

    def covered(p):
        for k in np.where(np.all((mn - .01 <= p) & (p <= mx + .01), axis=1))[0]:
            n, d = planes[k]
            if np.all(n @ p - d < .01):
                return True
        return False

    revealed = 0
    for b in BRUSHES:
        for f in b['faces']:
            if f['texture'] != 'NULL':
                continue
            P = np.array(f['points'], float); c = P.mean(axis=0); n = np.array(f['normal'])
            probes = [c] + [c + .9 * (v - c) for v in P] + \
                     [c + .9 * ((P[i] + P[(i + 1) % len(P)]) / 2 - c) for i in range(len(P))]
            if not all(covered(p + n) for p in probes):
                f['texture'] = b.get('backing', 'bm_metal'); revealed += 1
    return revealed


def num(x):
    return str(int(x)) if float(x).is_integer() else f'{x:.6f}'.rstrip('0').rstrip('.')


def map_face(f):
    # GoldSrc uses cross(p0-p1, p2-p1), so reverse our outward-CCW polygon.
    p=f['points'];pts=[p[2],p[1],p[0]]
    normal=f['normal'];axis=int(np.argmax(np.abs(normal)))
    if 'uv' in f:u,v,su,sv=f['uv']
    elif axis==2:u,v,su,sv=[1,0,0,0],[0,-1,0,0],1,1
    elif axis==0:u,v,su,sv=[0,1,0,0],[0,0,-1,0],1,1
    else:u,v,su,sv=[1,0,0,0],[0,0,-1,0],1,1
    a=' '.join('( '+' '.join(num(c) for c in pt)+' )' for pt in pts)
    return a+' '+f['texture']+' [ '+' '.join(num(c) for c in u)+' ] [ '+' '.join(num(c) for c in v)+' ] 0 '+num(su)+' '+num(sv)


def write_map():
    lines=['// de_blue_mesa - original desert defusal map','// Valve 220 source; compile before playing.']
    for ent in ENTITIES:
        lines.append('{')
        for k,v in ent['keys'].items():lines.append('"'+k+'" "'+v+'"')
        for bi in ent['brushes']:
            lines.append('// '+BRUSHES[bi]['tag']);lines.append('{')
            lines.extend(map_face(f) for f in BRUSHES[bi]['faces']);lines.append('}')
        lines.append('}')
    (SOURCE/'de_blue_mesa.map').write_text('\n'.join(lines)+'\n')
    manifest={'name':MAP_NAME,'format':'Valve220','bounds':[-1792,-1728,1792,1728],
              'brushes':BRUSHES,'entities':ENTITIES,'textures':{k:list(v.size) for k,v in TEX.items()}}
    (SOURCE/'geometry.json').write_text(json.dumps(manifest,separators=(',',':')))


def make_sky():
    # Six matching cube faces, sampled from one continuous procedural sky.
    # GoldSrc uses rt,bk,lf,ft,up,dn naming. Common world-oriented cube axes.
    n=256
    q=(np.arange(n)+.5)/n*2-1
    u,v=np.meshgrid(q,q);one=np.ones_like(u)
    faces={'rt':(one,-u,-v),'bk':(u,one,-v),'lf':(-one,u,-v),
           'ft':(-u,-one,-v),'up':(u,-v,one),'dn':(u,v,-one)}
    for name,(x,y,z) in faces.items():
        length=np.sqrt(x*x+y*y+z*z);x=x/length;y=y/length;z=z/length
        elevation=np.arcsin(z);az=np.arctan2(y,x)
        t=np.clip(z,0,1)[...,None]**.6
        a=np.array([210,194,143]);b=np.array([57,120,143])
        sky=a*(1-t)+b*t
        # Small, distant flat-topped mesas never obscure the upper sky.
        ridge=.015+.025*np.sin(az*6)+.018*np.sin(az*11+1)
        ridge+=np.maximum(0,np.sin(az*3+.5))**.2*.07
        mask=elevation<ridge
        rock=np.stack([134+8*np.sin(az*3),104+4*np.sin(az*3),75+2*np.sin(az*3)],axis=-1)
        sky=np.where(mask[...,None],rock,sky)
        low=elevation<-.08
        sky=np.where(low[...,None],np.array([150,114,74]),sky)
        Image.fromarray(np.uint8(np.clip(sky,0,255))).save(ROOT/'cstrike/gfx/env'/('bmesa'+name+'.tga'))


def texture_sheet():
    names=[n for n in TEX if n not in ('NULL','AAATRIGGER','CLIP','sky')]
    out=Image.new('RGB',(900,math.ceil(len(names)/6)*160+88),(21,32,32));d=ImageDraw.Draw(out)
    d.text((20,18),'BLUE MESA / ORIGINAL TEXTURE SET',font=font(25),fill=(229,216,178))
    for i,name in enumerate(names):
        x=20+(i%6)*146;y=72+(i//6)*160
        out.paste(TEX[name].resize((128,128)),(x,y))
        d.text((x,y+134),name,font=font(12,False),fill=(187,197,178))
    out.save(PREVIEW/'textures.png')


def topdown():
    w,h=1600,2270
    out=Image.new('RGB',(w,h),(18,29,28));d=ImageDraw.Draw(out)
    d.text((70,52),'BLUE MESA',font=font(76),fill=(236,218,167))
    d.text((74,145),'DE_BLUE_MESA  /  COUNTER-STRIKE 1.6  /  A MAP BY YAMAN',font=font(22),fill=(164,188,174))
    d.text((74,181),'Original geometry  •  residence, motel row, chicken stop and industrial laundry',font=font(19,False),fill=(153,167,151))
    scale=.397;ox=800;oy=927
    def xy(x,y):return (round(ox+x*scale),round(oy-y*scale))
    d.rectangle((*xy(-1792,1728),*xy(1792,-1728)),fill=(153,123,82))
    for gx in range(-1792,1793,128):d.line([xy(gx,-1728),xy(gx,1728)],fill=(147,116,77))
    for gy in range(-1728,1729,128):d.line([xy(-1792,gy),xy(1792,gy)],fill=(147,116,77))
    # Plot actual source footprints, with roofs omitted to show traversable rooms.
    skip=('sky enclosure','roof','canopy','lintel','header','overhead','crest','sign','ladder rung')
    tools={'NULL','CLIP','AAATRIGGER','sky'}
    for b in sorted(BRUSHES,key=lambda a:a['min'][2]):
        if b['tag'] in ('ground','clip') or not b['solid'] or any(s in b['tag'] for s in skip):continue
        if b['min'][2]>110:continue
        # Wall art is a thin plate with a single visible face; it would only add slivers.
        visible=[f['texture'] for f in b['faces'] if f['texture'] not in tools]
        if not visible or len(visible)==1:continue
        x0,y0,z0=b['min'];x1,y1,z1=b['max']
        t=visible[0];c=tuple(int(i) for i in np.array(TEX[t]).mean(axis=(0,1)))
        if 'wall' in b['tag'] or b['tag'] in ['motel','law office','residence','hermanos','fuel shop','laundry lab']:
            c=(65,77,66)
        d.rectangle((*xy(x0,y1),*xy(x1,y0)),fill=c,outline=(60,66,53),width=1)
    # Objective bounds are the source trigger footprints.
    for tag,c in [('A bomb site',(236,137,77)),('B bomb site',(108,204,212))]:
        b=next(b for b in BRUSHES if b['tag']==tag)
        x0,y0,z=b['min'];x1,y1,z=b['max']
        d.rectangle((*xy(x0,y1),*xy(x1,y0)),outline=c,width=4)
    for ent in ENTITIES:
        cl=ent['keys']['classname']
        if cl in ('info_player_start','info_player_deathmatch'):
            x,y,z=map(float,ent['keys']['origin'].split());px,py=xy(x,y)
            c=(115,207,217) if cl=='info_player_start' else (237,165,90)
            d.ellipse((px-5,py-5,px+5,py+5),fill=c,outline=(31,44,41),width=1)
    def label(text,x,y,color=(240,223,183),sz=22):
        px,py=xy(x,y);f=font(sz);bb=d.textbbox((0,0),text,font=f);tw=bb[2]-bb[0]
        d.rounded_rectangle((px-tw/2-12,py-10,px+tw/2+12,py+sz+10),radius=5,fill=(24,39,36))
        d.text((px-tw/2,py),text,font=f,fill=color)
    label('A / RV YARD',-1160,1210,(244,162,98),24)
    label('LAUNDRY  /  B BELOW',1070,1090,(122,215,219),21)
    label('MOTEL',-800,-420,sz=20)
    label("LAW OFFICE",-790,300,(238,196,150),19)
    label('RESIDENCE',-1416,-1210,(238,196,150),19)
    label('CANYON',-1560,-560,sz=19)
    label('MIDDLE',-30,-420,sz=18)
    label('UTILITY',628,-240,sz=17)
    label('FUEL STOP',820,-1195,sz=20)
    label('SCRAPYARD',1300,210,sz=18)
    label('HERMANOS',0,890,(244,206,110),19)
    label('CT SPAWN',0,1660,(123,210,220),20)
    label('T SPAWN',0,-1620,(242,177,106),20)
    # The chokepoints the lanes are built around.
    for text,x,y in [('LONG DOORS',-1436,-20),('MID DOORS',96,-110),('SHORT A',-816,540),
                     ('B ALLEY',560,300),('SCRAPYARD GATE',992,-560),('CT GATE',-964,1300),
                     ('EAST DOOR',1632,480)]:
        label(text,x,y,(250,236,150),15)
    d.line((72,1670,1528,1670),fill=(69,88,75),width=2)
    # The map above looks straight through the laundry roof, so bomb site B is
    # invisible there. It lives 288 units down; this inset is that level.
    d.text((74,1700),'SUB-LEVEL  /  THE SUPERLAB',font=font(26),fill=(236,218,167))
    d.text((76,1738),'288 units below the laundry  -  site B and every way down',
           font=font(17,False),fill=(153,167,151))
    iscale=.55;iox=700;ioy=2150
    def ixy(x,y):return (round(iox+(x-LAB_X0)*iscale),round(ioy-(y-LAB_Y0)*iscale))
    d.rectangle((*ixy(LAB_X0-16,LAB_Y1+16),*ixy(LAB_X1+16,LAB_Y0-16)),fill=(64,72,70))
    d.rectangle((*ixy(LAB_X0,LAB_Y1),*ixy(LAB_X1,LAB_Y0)),fill=(96,108,106),outline=(46,54,53),width=2)
    for b in sorted(BRUSHES,key=lambda a:a['min'][2]):
        if not b['solid'] or b['tag'] in ('superlab floor','superlab ceiling','clip'):continue
        if b['max'][2]>-64 or b['max'][2]<=LAB_FLOOR:continue
        vis=[f['texture'] for f in b['faces'] if f['texture'] not in tools]
        if not vis:continue
        x0,y0,_=b['min'];x1,y1,_=b['max']
        c=tuple(int(i) for i in np.array(TEX[vis[0]]).mean(axis=(0,1)))
        d.rectangle((*ixy(x0,y1),*ixy(x1,y0)),fill=c,outline=(52,60,58),width=1)
    site=next(b for b in BRUSHES if b['tag']=='site marking' and b['min'][2]<0)
    d.rectangle((*ixy(site['min'][0],site['max'][1]),*ixy(site['max'][0],site['min'][1])),
                outline=(108,204,212),width=4)
    def ilabel(text,x,y,color=(240,223,183),sz=17):
        px,py=ixy(x,y);f=font(sz);bb=d.textbbox((0,0),text,font=f);tw=bb[2]-bb[0]
        d.rounded_rectangle((px-tw/2-9,py-8,px+tw/2+9,py+sz+8),radius=4,fill=(24,39,36))
        d.text((px-tw/2,py),text,font=f,fill=color)
    # Below the zone rather than on it: the reactor stands in the middle of it.
    ilabel('B / PLANT FLOOR',(SITE_B_MARK[0]+SITE_B_MARK[2])//2,SITE_B_MARK[1]-40,(122,215,219),18)
    ilabel('CT HATCH',(HOLE_HATCH[0]+HOLE_HATCH[2])//2,HOLE_HATCH[3]-24,(244,206,110))
    ilabel('LIFT',(HOLE_ELEVATOR[0]+HOLE_ELEVATOR[2])//2,1040,(244,206,110))
    ilabel('STAIRS',(HOLE_STAIRS[0]+HOLE_STAIRS[2])//2,560,(244,206,110))
    ilabel('EAST STAIR',(TUNNEL_DOOR[0]+TUNNEL_DOOR[1])//2,420,(244,206,110))
    ilabel('REACTOR',1180,900)
    d.text((74,1800),'32 SPAWNS',font=font(21),fill=(227,210,170))
    d.text((74,1836),'2 BOMB SITES',font=font(21),fill=(227,210,170))
    d.text((74,1872),'SITE B IS UNDERGROUND',font=font(21),fill=(122,215,219))
    d.text((74,1908),'3 DESCENTS + A CT HATCH',font=font(21),fill=(227,210,170))
    d.text((74,1966),'main stair  /  lift  /  east stair  /  one-way hatch',font=font(16,False),fill=(151,173,157))
    d.text((74,2190),'SOURCE LAYOUT PREVIEW  /  Roofs omitted. Compile and playtest before server use.',
           font=font(18,False),fill=(151,173,157))
    out.save(PREVIEW/'layout.png')


# --- Overview: the spectator map and radar image ---------------------------
# CS 1.6 draws overviews/<map>.bmp as one 1024x768 plane. With ROTATED 1 it spans
# 8192/ZOOM world units across and 6144/ZOOM down, centred on ORIGIN, so a pixel
# is 8/ZOOM units with +X to the right and +Y up. The mapping was checked by
# projecting the stock de_inferno (ROTATED 1) and de_dust2 (ROTATED 0) BSPs onto
# their own overview images, where the floor outlines land exactly.
OVERVIEW_ZOOM = 1.70
OVERVIEW_ORIGIN = (0, 0, LAB_FLOOR)   # Valve sets z to the lowest floor, same as HEIGHT
OVERVIEW_VOID = (0, 255, 0)           # every stock overview paints out-of-bounds this


def overview():
    """Radar / spectator overview, with the superlab drawn into the laundry.

    The engine draws a single layer, and a player's dot lands on it by X and Y
    alone. Site B is directly under the laundry, so inside the laundry walls the
    plan shows the lab level - the objective and its three descents are what
    anyone reading the map there needs. The laundry's own floor props stay as
    faint outlines so the floor above is not lost entirely.
    """
    ss = 2                                   # drawn at twice size, then downsampled
    W, H = 1024 * ss, 768 * ss
    k = OVERVIEW_ZOOM / 8 * ss
    ox, oy, oz = OVERVIEW_ORIGIN
    def P(x, y): return (W / 2 + (x - ox) * k, H / 2 - (y - oy) * k)
    def R(x0, y0, x1, y1): return (*P(x0, y1), *P(x1, y0))
    C = {'ground': (160, 134, 98), 'road': (122, 117, 104), 'floor': (200, 189, 164),
         'low': (112, 98, 78), 'tall': (74, 64, 52), 'wall': (36, 34, 32), 'glass': (82, 116, 124),
         'pool': (86, 150, 168), 'marking': (196, 168, 70), 'prop': (222, 236, 236),
         'lab': (104, 132, 142), 'labcover': (52, 68, 76), 'labwall': (22, 30, 36), 'stair': (150, 170, 176)}
    tools = {'NULL', 'CLIP', 'AAATRIGGER', 'sky'}
    im = Image.new('RGB', (W, H), C['ground'])
    d = ImageDraw.Draw(im)

    def shown(b):
        visible = [f for f in b['faces'] if f['texture'] not in tools]
        # Wall art is a plate with one visible face; it would only add slivers.
        return (b['solid'] and len(visible) > 1 and not any(s in b['tag'] for s in ('ladder', 'rung'))
                and ENTITIES[b['entity']]['keys']['classname'] not in ('func_door', 'func_ladder'))
    building_tags = {t for *_, t in BUILDINGS}
    def wall_like(t):
        return (t in building_tags or t.endswith(' sill') or 'wall' in t
                or 'boundary' in t or 'screen' in t or t == 'rock mass')
    lx0, ly0, lx1, ly1, _ = next(b for b in BUILDINGS if b[4] == 'laundry lab')
    def in_laundry(b):
        return (b['min'][0] >= lx0 + 16 and b['max'][0] <= lx1 - 16 and
                b['min'][1] >= ly0 + 16 and b['max'][1] <= ly1 - 16)
    def fill(b, c, outline=None):
        d.rectangle(R(*b['min'][:2], *b['max'][:2]), fill=c, outline=outline, width=ss if outline else 0)

    # --- Surface floors: building interiors, then roads and floor overlays.
    surface = sorted((b for b in BRUSHES if shown(b) and b['max'][2] > 0),
                     key=lambda b: b['max'][2])
    floors, props = [], []
    for b in surface:
        z0, z1, t = b['min'][2], b['max'][2], b['tag']
        if z0 >= 72 and t != 'maintenance platform':
            continue                                 # roofs, signs and anything overhead
        (floors if 'floor' in t or 'stair' in t or z1 <= 20 or t == 'maintenance platform'
         else props).append(b)
    for x0, y0, x1, y1, _ in BUILDINGS:
        d.rectangle(R(x0, y0, x1, y1), fill=C['floor'])
    for b in floors:
        if 'site' in b['tag']:
            continue
        tex = next(f['texture'] for f in b['faces'] if f['texture'] not in tools)
        c = (C['marking'] if 'marking' in b['tag'] else C['pool'] if tex == 'bm_pool' else
             C['road'] if tex in ('bm_asphalt', 'bm_concrete') else C['floor'])
        fill(b, c, C['tall'] if 'stair' in b['tag'] or b['tag'] == 'maintenance platform' else None)

    # --- The superlab level, inside the laundry, with its tunnel and shaft.
    dx0, dx1 = TUNNEL_DOOR
    tx0, ty0, tx1, ty1 = HOLE_TUNNEL
    for box_ in [(LAB_X0, LAB_Y0, LAB_X1, LAB_Y1), (dx0, ty0, dx1, LAB_Y0)]:
        d.rectangle(R(*box_), fill=C['lab'])
    under = sorted((b for b in BRUSHES if shown(b) and b['max'][2] <= 0
                    and b['min'][2] >= LAB_FLOOR - 16), key=lambda b: b['max'][2])
    for b in under:
        z0, z1, t = b['min'][2], b['max'][2], b['tag']
        if z0 >= LAB_FLOOR + 72 or (z1 <= LAB_FLOOR + 20 and 'stair' not in t):
            continue                                 # ceiling, ducts, floor paint
        if 'stair' in t:
            fill(b, C['stair'], C['labwall'])        # outlined, so each tread reads
        elif 'superlab wall' in t or 'shaft' in t or 'access tunnel' in t:
            fill(b, C['labwall'])
        else:
            fill(b, C['labcover'])
    d.rectangle(R(*HOLE_ELEVATOR), fill=C['stair'], outline=C['labwall'], width=ss)

    # --- Surface cover and walls. Inside the laundry, props are outlines only.
    for b in props:
        t = b['tag']
        if in_laundry(b) and not wall_like(t):
            d.rectangle(R(*b['min'][:2], *b['max'][:2]), outline=C['prop'], width=ss)
            continue
        fill(b, C['glass'] if t.endswith('window') or 'windshield' in t else
             C['wall'] if wall_like(t) else C['low'] if b['max'][2] < 72 else C['tall'])

    # --- Buy zones and bomb sites, tinted over the plan.
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    def trigger(tag): return next(b for b in BRUSHES if b['tag'] == tag)
    for tag, c, a in [('T buy zone', (236, 150, 70), 44), ('CT buy zone', (90, 170, 230), 44),
                      ('A bomb site', (236, 137, 77), 58), ('B bomb site', (108, 214, 222), 70)]:
        b = trigger(tag)
        ld.rectangle(R(*b['min'][:2], *b['max'][:2]), fill=(*c, a), outline=(*c, 230), width=2 * ss)
    im = Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')
    d = ImageDraw.Draw(im)

    def badge(cx, cy, r=10 * ss):
        """A way down: dark disc, pale downward triangle. Canvas coordinates."""
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(24, 30, 32), outline=(236, 222, 150), width=ss)
        t = r * .55
        d.polygon([(cx - t, cy - t * .6), (cx + t, cy - t * .6), (cx, cy + t * .8)], fill=(236, 222, 150))
    for hx0, hy0, hx1, hy1 in DESCENT_HOLES:
        badge(*P((hx0 + hx1) / 2, (hy0 + hy1) / 2))
    def letter(text, x, y, c):
        f = font(46 * ss)
        cx, cy = P(x, y)
        bb = d.textbbox((0, 0), text, font=f, stroke_width=4 * ss)
        d.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), text, font=f, fill=c,
               stroke_width=4 * ss, stroke_fill=(18, 24, 24))
    a_mark = next(b for b in BRUSHES if b['tag'] == 'site marking' and b['min'][2] >= 0)
    b_mark = next(b for b in BRUSHES if b['tag'] == 'site marking' and b['min'][2] < 0)
    letter('A', (a_mark['min'][0] + a_mark['max'][0]) / 2, (a_mark['min'][1] + a_mark['max'][1]) / 2,
           (246, 160, 96))
    letter('B', (b_mark['min'][0] + b_mark['max'][0]) / 2, (b_mark['min'][1] + b_mark['max'][1]) / 2,
           (132, 226, 232))

    # --- A small key in the left margin, which is outside the playable area.
    panel = (8 * ss, 560 * ss, 124 * ss, 760 * ss)
    d.rounded_rectangle(panel, radius=6 * ss, fill=(24, 32, 32), outline=(70, 88, 84), width=ss)
    d.rectangle((18 * ss, 574 * ss, 38 * ss, 594 * ss), fill=C['lab'], outline=(108, 214, 222), width=2 * ss)
    y = 574
    for line in ('SITE B IS', 'BELOW THE', 'LAUNDRY'):
        d.text((46 * ss, y * ss), line, font=font(10 * ss), fill=(214, 226, 222)); y += 15
    badge(28 * ss, 656 * ss)
    y = 646
    for line in ('WAY DOWN:', 'TWO STAIRS,', 'THE LIFT,', 'CT HATCH'):
        d.text((46 * ss, y * ss), line, font=font(10 * ss), fill=(214, 226, 222)); y += 15
    d.text((18 * ss, 712 * ss), 'DE_BLUE_MESA', font=font(11 * ss), fill=(236, 218, 167))
    d.text((18 * ss, 730 * ss), 'a map by YAMAN', font=font(10 * ss, False), fill=(150, 170, 160))

    # --- Down to 1024x768, void painted exact, 8-bit palette like the stock files.
    im = im.resize((1024, 768), Image.Resampling.LANCZOS)
    cols = np.arange(1024) + .5
    rows = np.arange(768) + .5
    wx = ox + (cols - 512) * 8 / OVERVIEW_ZOOM
    wy = oy - (rows - 384) * 8 / OVERVIEW_ZOOM
    void = ~((np.abs(wy)[:, None] <= 1728) & (np.abs(wx)[None, :] <= 1792))
    pc = np.zeros((768, 1024), dtype=bool)
    pc[panel[1] // ss:panel[3] // ss, panel[0] // ss:panel[2] // ss] = True
    void &= ~pc
    q = im.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = (q.getpalette() + [0] * 765)[:765] + list(OVERVIEW_VOID)
    idx = np.array(q)
    idx[void] = 255
    out = Image.fromarray(idx, 'P')
    out.putpalette(pal)
    target = ROOT / 'cstrike/overviews'
    # Earlier releases' overviews are someone else's files now, not this package's.
    for old in target.glob('de_blue_mesa*.*'):
        if old.stem != MAP_NAME:old.unlink()
    out.save(target / f'{MAP_NAME}.bmp')
    out.convert('RGB').save(PREVIEW / 'overview.png')
    (target / f'{MAP_NAME}.txt').write_text(
        f'// overview description file for {MAP_NAME}.bsp\n'
        '// Generated by source/generate_map.py - see overview() for the mapping.\n\n'
        'global \n{\n'
        f'\tZOOM\t{OVERVIEW_ZOOM:.2f}\n'
        f'\tORIGIN\t{ox} \t{oy}\t{oz}\n'
        '\tROTATED\t1\n}\n\n'
        'layer \n{\n'
        f'\tIMAGE\t"overviews/{MAP_NAME}.bmp"\n'
        f'\tHEIGHT\t{oz}\n}}\n')


if __name__=='__main__':
    for p in [SOURCE,PREVIEW,ROOT/'cstrike/gfx/env',ROOT/'cstrike/overviews']:p.mkdir(parents=True,exist_ok=True)
    make_textures();write_wad();make_map();reveal_exposed_faces();write_map();make_sky();texture_sheet();topdown();overview()
    # The sounds are their own script; imported here so one command rebuilds everything.
    from make_music import write_radio, write_clip
    sounds=ROOT/'cstrike/sound'/SOUND_DIR
    sounds.mkdir(parents=True,exist_ok=True)
    # Drop sounds from earlier releases' folders, and clips CLIPS no longer lists
    # (0.8 had a 'bomb' one).
    for f in (ROOT/'cstrike/sound/bluemesa').rglob('*.wav'):
        if f.parent!=sounds or (f.stem not in CLIPS and f.name!='mesa_radio.wav'):f.unlink()
    for d in sorted((ROOT/'cstrike/sound/bluemesa').glob('*/'),reverse=True):
        if d.is_dir() and not any(d.iterdir()):d.rmdir()
    write_radio(sounds/'mesa_radio.wav')
    shipped=[]
    for name,c in CLIPS.items():
        out=sounds/f'{name}.wav'
        if clip_source(name).exists():
            write_clip(clip_source(name),out,c['seconds'],c['start'])
            shipped.append(f'sound/{SOUND_DIR}/{name}.wav')
        else:
            out.unlink(missing_ok=True)
    # The resource list tells servers what to send to players; it is written
    # here so it always matches the files the map actually uses.
    res=['// Blue Mesa resource list. Written by source/generate_map.py.',
         '// Custom WAD textures are embedded by the supplied compile helper.',
         *[f'gfx/env/bmesa{s}.tga' for s in ('rt','bk','lf','ft','up','dn')],
         f'maps/{MAP_NAME}.txt',f'overviews/{MAP_NAME}.bmp',f'overviews/{MAP_NAME}.txt',
         f'sound/{SOUND_DIR}/mesa_radio.wav']
    res+=shipped
    for old in (ROOT/'cstrike/maps').glob('de_blue_mesa*.res'):
        if old.stem!=MAP_NAME:old.unlink()
    (ROOT/'cstrike/maps'/f'{MAP_NAME}.res').write_text('\n'.join(res)+'\n')
    print(json.dumps({'map':MAP_NAME,'brushes':len(BRUSHES),'entities':len(ENTITIES),'textures':len(TEX)},indent=2))
