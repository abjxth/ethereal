"""
Color palette system for Ethereal.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from PIL import Image
import numpy as np


@dataclass
class ColorPalette:
    """A named color palette."""
    name: str
    colors: list[tuple[int, int, int]]  # RGB tuples
    background: tuple[int, int, int] = (18, 18, 22)
    playhead_color: tuple[int, int, int] = (255, 120, 50)
    text_color: tuple[int, int, int] = (255, 255, 255)
    grid_color: tuple[int, int, int] = (255, 255, 255)


# ---------------------------------------------------------------------------
# Curated palettes
# ---------------------------------------------------------------------------

PALETTES: dict[str, ColorPalette] = {
    "Ethereal": ColorPalette(
        name="Ethereal",
        colors=[
            (0, 230, 210),    # cyan/teal
            (255, 120, 50),   # warm orange
            (130, 180, 255),  # soft blue
            (255, 80, 120),   # coral pink
            (180, 130, 255),  # lavender
            (100, 255, 150),  # mint green
            (255, 200, 80),   # gold
            (200, 200, 210),  # silver
        ],
        background=(18, 18, 22),
        playhead_color=(255, 120, 50),
    ),
    "Midnight": ColorPalette(
        name="Midnight",
        colors=[
            (80, 140, 255),   # royal blue
            (255, 100, 80),   # coral
            (120, 220, 180),  # seafoam
            (255, 180, 60),   # amber
            (200, 100, 255),  # purple
            (80, 220, 255),   # sky blue
            (255, 140, 180),  # rose
            (180, 200, 80),   # lime
        ],
        background=(12, 12, 20),
        playhead_color=(255, 100, 80),
    ),
    "Neon": ColorPalette(
        name="Neon",
        colors=[
            (0, 255, 136),    # neon green
            (255, 0, 102),    # neon pink
            (0, 204, 255),    # neon blue
            (255, 255, 0),    # neon yellow
            (204, 0, 255),    # neon purple
            (255, 102, 0),    # neon orange
            (0, 255, 255),    # neon cyan
            (255, 0, 255),    # neon magenta
        ],
        background=(8, 8, 12),
        playhead_color=(255, 0, 102),
    ),
    "Pastel": ColorPalette(
        name="Pastel",
        colors=[
            (180, 220, 255),  # baby blue
            (255, 180, 180),  # blush
            (180, 255, 200),  # mint
            (255, 220, 160),  # peach
            (220, 180, 255),  # lilac
            (255, 255, 180),  # cream
            (180, 255, 255),  # ice
            (255, 200, 220),  # rose quartz
        ],
        background=(25, 25, 30),
        playhead_color=(255, 180, 180),
    ),
    "Monochrome": ColorPalette(
        name="Monochrome",
        colors=[
            (255, 255, 255),  # white
            (200, 200, 200),  # light gray
            (160, 160, 160),  # gray
            (120, 120, 120),  # dark gray
            (220, 220, 220),  # silver
            (180, 180, 180),  # medium gray
            (240, 240, 240),  # near white
            (140, 140, 140),  # mid gray
        ],
        background=(15, 15, 15),
        playhead_color=(255, 255, 255),
    ),
    "Sunset": ColorPalette(
        name="Sunset",
        colors=[
            (255, 100, 50),   # orange red
            (255, 180, 40),   # golden
            (255, 60, 90),    # crimson
            (255, 140, 100),  # salmon
            (200, 60, 120),   # magenta
            (255, 200, 120),  # light gold
            (180, 40, 80),    # burgundy
            (255, 120, 160),  # flamingo
        ],
        background=(20, 12, 15),
        playhead_color=(255, 180, 40),
    ),
    "Ocean": ColorPalette(
        name="Ocean",
        colors=[
            (0, 180, 220),    # ocean blue
            (0, 220, 180),    # teal
            (100, 160, 255),  # sky
            (0, 150, 150),    # deep teal
            (80, 200, 220),   # aqua
            (120, 180, 200),  # steel blue
            (0, 255, 200),    # turquoise
            (60, 140, 180),   # slate
        ],
        background=(8, 15, 22),
        playhead_color=(0, 220, 180),
    ),
    "Studio Classic": ColorPalette(
        name="Studio Classic",
        colors=[
            (0, 210, 200),    # teal (keys)
            (255, 120, 50),   # orange (bass/808)
            (100, 160, 190),  # muted blue-gray (arp)
            (160, 160, 160),  # gray (drums)
            (0, 190, 180),    # darker teal
            (220, 100, 40),   # darker orange
            (80, 140, 170),   # steel
            (120, 120, 120),  # dim gray
        ],
        background=(18, 18, 22),
        playhead_color=(255, 120, 50),
    ),
    "Vapor": ColorPalette(
        name="Vapor",
        colors=[
            (255, 100, 200),  # hot pink
            (100, 200, 255),  # baby blue
            (200, 100, 255),  # purple
            (255, 200, 100),  # warm yellow
            (100, 255, 200),  # mint
            (255, 150, 150),  # light coral
            (150, 100, 255),  # violet
            (100, 255, 255),  # cyan
        ],
        background=(15, 10, 25),
        playhead_color=(255, 100, 200),
    ),
    "Fire": ColorPalette(
        name="Fire",
        colors=[
            (255, 60, 20),    # flame red
            (255, 160, 0),    # orange
            (255, 220, 40),   # yellow
            (255, 100, 40),   # dark orange
            (200, 30, 10),    # deep red
            (255, 200, 100),  # light gold
            (180, 50, 20),    # maroon
            (255, 140, 60),   # tangerine
        ],
        background=(20, 8, 5),
        playhead_color=(255, 220, 40),
    ),
    "Forest": ColorPalette(
        name="Forest",
        colors=[
            (60, 200, 80),    # leaf green
            (40, 160, 120),   # forest teal
            (120, 220, 60),   # lime
            (80, 180, 100),   # sage
            (160, 200, 40),   # chartreuse
            (40, 140, 80),    # deep green
            (100, 200, 140),  # mint
            (180, 220, 100),  # spring
        ],
        background=(10, 18, 12),
        playhead_color=(120, 220, 60),
    ),
    "Frost": ColorPalette(
        name="Frost",
        colors=[
            (180, 220, 255),  # ice blue
            (220, 240, 255),  # near white
            (140, 200, 240),  # light blue
            (160, 180, 220),  # steel
            (200, 230, 255),  # frost
            (120, 180, 220),  # winter blue
            (240, 250, 255),  # snow
            (100, 160, 200),  # slate blue
        ],
        background=(12, 16, 22),
        playhead_color=(180, 220, 255),
    ),
    "Coral Reef": ColorPalette(
        name="Coral Reef",
        colors=[
            (255, 120, 100),  # coral
            (0, 200, 180),    # sea green
            (255, 180, 80),   # sandy
            (80, 180, 255),   # lagoon
            (255, 100, 150),  # pink coral
            (120, 220, 160),  # seafoam
            (255, 200, 140),  # peach sand
            (60, 160, 200),   # deep water
        ],
        background=(15, 20, 25),
        playhead_color=(255, 120, 100),
    ),
    "Cyberpunk": ColorPalette(
        name="Cyberpunk",
        colors=[
            (255, 0, 100),    # hot pink
            (0, 255, 200),    # electric cyan
            (255, 255, 0),    # yellow
            (150, 0, 255),    # electric purple
            (255, 80, 0),     # orange
            (0, 200, 255),    # bright blue
            (255, 0, 200),    # magenta
            (0, 255, 100),    # neon green
        ],
        background=(5, 5, 15),
        playhead_color=(255, 0, 100),
    ),
    "Amber": ColorPalette(
        name="Amber",
        colors=[
            (255, 180, 0),    # amber
            (200, 140, 0),    # dark amber
            (255, 220, 100),  # light amber
            (180, 120, 0),    # brown amber
            (255, 200, 60),   # golden
            (160, 100, 0),    # deep amber
            (255, 240, 160),  # cream
            (220, 160, 40),   # bronze
        ],
        background=(20, 15, 5),
        playhead_color=(255, 180, 0),
    ),
    "Arctic": ColorPalette(
        name="Arctic",
        colors=[
            (200, 240, 255),  # pale ice
            (140, 200, 255),  # arctic blue
            (255, 255, 255),  # white
            (100, 180, 220),  # cold blue
            (180, 220, 240),  # light frost
            (80, 160, 200),   # deep arctic
            (220, 240, 250),  # snow
            (160, 200, 230),  # glacier
        ],
        background=(8, 12, 18),
        playhead_color=(200, 240, 255),
    ),
    "Sakura": ColorPalette(
        name="Sakura",
        colors=[
            (255, 180, 200),  # cherry blossom
            (255, 140, 170),  # pink
            (220, 160, 180),  # dusty rose
            (255, 200, 210),  # light pink
            (200, 120, 150),  # mauve
            (255, 220, 230),  # blush
            (180, 100, 130),  # deep rose
            (240, 180, 200),  # soft pink
        ],
        background=(20, 12, 16),
        playhead_color=(255, 180, 200),
    ),
    "Emerald": ColorPalette(
        name="Emerald",
        colors=[
            (0, 200, 100),    # emerald
            (0, 160, 80),     # dark emerald
            (80, 240, 140),   # light emerald
            (0, 180, 120),    # jade
            (40, 220, 100),   # bright green
            (0, 140, 60),     # deep emerald
            (120, 255, 180),  # light jade
            (60, 200, 140),   # seafoam
        ],
        background=(8, 18, 12),
        playhead_color=(0, 200, 100),
    ),
    "Crimson": ColorPalette(
        name="Crimson",
        colors=[
            (220, 40, 40),    # crimson
            (255, 80, 60),    # bright red
            (180, 20, 30),    # dark crimson
            (255, 120, 100),  # salmon
            (200, 50, 50),    # ruby
            (255, 60, 80),    # red-pink
            (160, 30, 20),    # maroon
            (255, 100, 80),   # coral red
        ],
        background=(20, 8, 8),
        playhead_color=(255, 80, 60),
    ),
    "Twilight": ColorPalette(
        name="Twilight",
        colors=[
            (120, 80, 200),   # twilight purple
            (255, 140, 80),   # sunset orange
            (80, 60, 180),    # deep purple
            (200, 100, 160),  # plum
            (60, 100, 200),   # dusk blue
            (255, 180, 120),  # peach
            (140, 60, 160),   # violet
            (100, 120, 200),  # steel blue
        ],
        background=(15, 10, 20),
        playhead_color=(255, 140, 80),
    ),
}


def get_palette(name: str) -> ColorPalette:
    """Get a palette by name. Falls back to 'Ethereal' default."""
    return PALETTES.get(name, PALETTES["Ethereal"])


def get_palette_names() -> list[str]:
    """Return list of all palette names."""
    return list(PALETTES.keys())


def extract_palette_from_image(image_path: str, num_colors: int = 8) -> ColorPalette:
    """Extract dominant colors from an image to create a palette."""
    img = Image.open(image_path).convert('RGB')
    img = img.resize((150, 150))
    pixels = np.array(img).reshape(-1, 3)

    # Simple k-means-like clustering
    from collections import Counter
    # Quantize to reduce color space
    quantized = (pixels // 32) * 32 + 16
    color_counts = Counter(map(tuple, quantized.tolist()))
    dominant = [c for c, _ in color_counts.most_common(num_colors * 3)]

    # Filter out too-dark and too-similar colors
    filtered = []
    for c in dominant:
        r, g, b = c
        if r + g + b < 60:  # skip very dark
            continue
        too_similar = False
        for existing in filtered:
            dr = abs(r - existing[0])
            dg = abs(g - existing[1])
            db = abs(b - existing[2])
            if dr + dg + db < 80:
                too_similar = True
                break
        if not too_similar:
            filtered.append(c)
        if len(filtered) >= num_colors:
            break

    # Pad if needed
    while len(filtered) < num_colors:
        filtered.append((180, 180, 180))

    # Determine background from darkest region
    dark_pixels = pixels[np.sum(pixels, axis=1) < 200]
    if len(dark_pixels) > 0:
        bg = tuple(int(x) for x in dark_pixels.mean(axis=0))
    else:
        bg = (18, 18, 22)

    name = os.path.splitext(os.path.basename(image_path))[0]
    return ColorPalette(
        name=f"Photo: {name}",
        colors=filtered[:num_colors],
        background=bg,
        playhead_color=filtered[1] if len(filtered) > 1 else (255, 120, 50),
    )
