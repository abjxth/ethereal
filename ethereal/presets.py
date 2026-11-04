"""
Preset system — save/load visualization settings.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Preset:
    """A saved visualization configuration."""
    name: str
    palette_name: str
    zoom: float = 1.0
    note_height_mode: int = 1  # 0=small, 1=medium, 2=large
    show_note_labels: bool = True
    show_chord_names: bool = True
    show_beat_grid: bool = True
    show_velocity: bool = True
    glow_intensity: float = 0.7
    waveform_style: str = "neon_bars"
    waveform_height_scale: float = 1.0
    waveform_opacity: float = 0.75
    waveform_position: str = "bottom"
    hit_marker_type: str = "glow_dot"
    hit_marker_emoji: str = "🔥"
    hit_marker_size: float = 1.0
    glow_style: str = "bloom"
    glow_color_mode: str = "match_note"
    background_type: str = "solid"  # solid, gradient, image
    background_color: tuple[int, int, int] = (18, 18, 22)
    background_blur: float = 0.0
    aspect_ratio: str = "9:16"
    resolution: str = "1080p"
    fps: int = 60

    def to_dict(self) -> dict:
        d = asdict(self)
        d["background_color"] = list(d["background_color"])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Preset:
        if "background_color" in d and isinstance(d["background_color"], list):
            d["background_color"] = tuple(d["background_color"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Default presets
# ---------------------------------------------------------------------------

DEFAULT_PRESETS = [
    Preset(name="Default", palette_name="Ethereal"),
    Preset(name="Studio Classic", palette_name="Studio Classic", glow_intensity=0.8),
    Preset(name="Neon Night", palette_name="Neon", glow_intensity=1.0,
           background_color=(5, 5, 10)),
    Preset(name="Clean", palette_name="Monochrome", show_chord_names=False,
           glow_intensity=0.3),
    Preset(name="Pastel Dream", palette_name="Pastel", glow_intensity=0.5,
           note_height_mode=2),
    Preset(name="Cyberpunk", palette_name="Cyberpunk", glow_intensity=1.0),
    Preset(name="Sunset Vibes", palette_name="Sunset", glow_intensity=0.6),
    Preset(name="Ocean Depth", palette_name="Ocean", glow_intensity=0.8),
    Preset(name="Minimal", palette_name="Monochrome", show_note_labels=False,
           show_chord_names=False, show_beat_grid=False, glow_intensity=0.0),
    Preset(name="Full Info", palette_name="Ethereal", show_note_labels=True,
           show_chord_names=True, show_beat_grid=True, show_velocity=True,
           glow_intensity=0.7, note_height_mode=2),
]


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _presets_dir() -> str:
    """Get the user presets directory."""
    app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    d = os.path.join(app_data, "Ethereal", "presets")
    os.makedirs(d, exist_ok=True)
    return d


def save_preset(preset: Preset):
    """Save a preset to disk."""
    d = _presets_dir()
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in preset.name)
    filepath = os.path.join(d, f"{safe_name}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(preset.to_dict(), f, indent=2)


def load_presets() -> list[Preset]:
    """Load all presets (defaults + user-saved)."""
    presets = list(DEFAULT_PRESETS)
    d = _presets_dir()
    if os.path.isdir(d):
        for filename in os.listdir(d):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(d, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    p = Preset.from_dict(data)
                    # Don't duplicate defaults
                    if not any(dp.name == p.name for dp in DEFAULT_PRESETS):
                        presets.append(p)
                except Exception:
                    pass
    return presets


def delete_preset(name: str):
    """Delete a user preset by name."""
    d = _presets_dir()
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
    filepath = os.path.join(d, f"{safe_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
