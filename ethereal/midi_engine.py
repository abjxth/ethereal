"""
MIDI Engine — Parses MIDI files into structured data for visualization.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import mido


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Note:
    """A single MIDI note event."""
    track_idx: int
    channel: int
    pitch: int          # 0-127
    velocity: int       # 0-127
    start_tick: int
    end_tick: int
    start_time: float   # seconds
    end_time: float     # seconds
    pitch_bend: list[tuple[float, float]] = field(default_factory=list)  # (time, semitones)
    midi_id: str = ""
    color_override: Optional[tuple[int, int, int]] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def note_name(self) -> str:
        names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (self.pitch // 12) - 1
        name = names[self.pitch % 12]
        return f"{name}{octave}"

    @property
    def is_drum(self) -> bool:
        return self.channel == 9


@dataclass
class TempoChange:
    """A tempo change event."""
    tick: int
    time: float         # seconds
    tempo: int          # microseconds per beat
    bpm: float


@dataclass
class TimeSignature:
    """A time signature event."""
    tick: int
    time: float
    numerator: int
    denominator: int


@dataclass
class TrackInfo:
    """Metadata about a MIDI track."""
    index: int
    name: str
    channel: int
    color_idx: int      # index into palette
    note_count: int
    min_pitch: int
    max_pitch: int
    is_drum: bool
    visible: bool = True


@dataclass
class MidiData:
    """Parsed MIDI file data ready for visualization."""
    filename: str
    song_name: str
    ticks_per_beat: int
    total_ticks: int
    total_time: float       # seconds
    initial_bpm: float
    key_signature: str
    notes: list[Note]
    tracks: list[TrackInfo]
    tempo_changes: list[TempoChange]
    time_signatures: list[TimeSignature]
    min_pitch: int
    max_pitch: int


# ---------------------------------------------------------------------------
# Key signature names
# ---------------------------------------------------------------------------

_KEY_NAMES = {
    (0, False): 'C', (1, False): 'G', (2, False): 'D', (3, False): 'A',
    (4, False): 'E', (5, False): 'B', (6, False): 'F#', (7, False): 'C#',
    (-1, False): 'F', (-2, False): 'Bb', (-3, False): 'Eb', (-4, False): 'Ab',
    (-5, False): 'Db', (-6, False): 'Gb', (-7, False): 'Cb',
    (0, True): 'Am', (1, True): 'Em', (2, True): 'Bm', (3, True): 'F#m',
    (4, True): 'C#m', (5, True): 'G#m', (6, True): 'D#m', (7, True): 'A#m',
    (-1, True): 'Dm', (-2, True): 'Gm', (-3, True): 'Cm', (-4, True): 'Fm',
    (-5, True): 'Bbm', (-6, True): 'Ebm', (-7, True): 'Abm',
}


# ---------------------------------------------------------------------------
# Chord detection
# ---------------------------------------------------------------------------

_CHORD_TEMPLATES = {
    'maj':  {0, 4, 7},
    'min':  {0, 3, 7},
    'dim':  {0, 3, 6},
    'aug':  {0, 4, 8},
    'sus4': {0, 5, 7},
    'sus2': {0, 2, 7},
    '7':    {0, 4, 7, 10},
    'maj7': {0, 4, 7, 11},
    'min7': {0, 3, 7, 10},
    'dim7': {0, 3, 6, 9},
}

_NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def detect_chord(pitches: list[int]) -> str:
    """Detect chord name from a list of MIDI pitches."""
    if len(pitches) < 2:
        return ""
    pitch_classes = sorted(set(p % 12 for p in pitches))
    if len(pitch_classes) < 2:
        return _NOTE_NAMES[pitch_classes[0]]

    best_match = ""
    best_score = 0
    for root in pitch_classes:
        intervals = set((p - root) % 12 for p in pitch_classes)
        for name, template in _CHORD_TEMPLATES.items():
            score = len(intervals & template)
            if score > best_score and score >= len(template) - 1:
                best_score = score
                root_name = _NOTE_NAMES[root]
                if name == 'maj':
                    best_match = root_name
                elif name == 'min':
                    best_match = f"{root_name}m"
                else:
                    best_match = f"{root_name}{name}"
    return best_match


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_midi(filepath: str) -> MidiData:
    """Parse a MIDI file into MidiData."""
    mid = mido.MidiFile(filepath)

    # ---- Build tick→time mapping from tempo changes ----
    tempo_changes: list[TempoChange] = []
    time_sigs: list[TimeSignature] = []
    key_sig = "C"

    # Collect all tempo/meta from all tracks
    all_meta: list[tuple[int, mido.Message]] = []
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type in ('set_tempo', 'time_signature', 'key_signature', 'track_name'):
                all_meta.append((abs_tick, msg))
    all_meta.sort(key=lambda x: x[0])

    current_tempo = 500000  # default 120 BPM
    current_time = 0.0
    last_tick = 0

    # Pre-scan for tempo map
    tempo_map: list[tuple[int, int]] = [(0, current_tempo)]
    for abs_tick, msg in all_meta:
        if msg.type == 'set_tempo':
            tempo_map.append((abs_tick, msg.tempo))

    def tick_to_time(target_tick: int) -> float:
        """Convert a tick position to time in seconds."""
        t = 0.0
        prev_tick = 0
        prev_tempo = 500000
        for tick, tempo in tempo_map:
            if tick >= target_tick:
                break
            dt = (tick - prev_tick) / mid.ticks_per_beat * (prev_tempo / 1_000_000)
            t += dt
            prev_tick = tick
            prev_tempo = tempo
        dt = (target_tick - prev_tick) / mid.ticks_per_beat * (prev_tempo / 1_000_000)
        t += dt
        return t

    # Process meta events
    for abs_tick, msg in all_meta:
        msg_time = tick_to_time(abs_tick)
        if msg.type == 'set_tempo':
            tempo_changes.append(TempoChange(
                tick=abs_tick, time=msg_time,
                tempo=msg.tempo, bpm=round(mido.tempo2bpm(msg.tempo), 1)
            ))
        elif msg.type == 'time_signature':
            time_sigs.append(TimeSignature(
                tick=abs_tick, time=msg_time,
                numerator=msg.numerator, denominator=msg.denominator
            ))
        elif msg.type == 'key_signature':
            key_sig = _KEY_NAMES.get((msg.key, msg.key < 0 or 'minor' in str(msg)), msg.key)
            if hasattr(msg, 'key') and isinstance(msg.key, str):
                key_sig = msg.key

    if not tempo_changes:
        tempo_changes.append(TempoChange(tick=0, time=0.0, tempo=500000, bpm=120.0))
    if not time_sigs:
        time_sigs.append(TimeSignature(tick=0, time=0.0, numerator=4, denominator=4))

    # ---- Parse notes from all tracks ----
    notes: list[Note] = []
    track_infos: list[TrackInfo] = []
    color_idx = 0

    for trk_idx, track in enumerate(mid.tracks):
        track_name = ""
        active_notes: dict[tuple[int, int], tuple[int, int]] = {}  # (ch, pitch) → (start_tick, velocity)
        pitch_bends: dict[int, list[tuple[float, float]]] = {}     # channel → [(time, semitones)]
        abs_tick = 0
        track_notes: list[Note] = []
        track_channel = 0

        for msg in track:
            abs_tick += msg.time
            msg_time = tick_to_time(abs_tick)

            if msg.type == 'track_name':
                track_name = msg.name

            elif msg.type == 'note_on' and msg.velocity > 0:
                key = (msg.channel, msg.note)
                active_notes[key] = (abs_tick, msg.velocity)
                track_channel = msg.channel

            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active_notes:
                    start_tick, velocity = active_notes.pop(key)
                    start_time = tick_to_time(start_tick)
                    note = Note(
                        track_idx=trk_idx,
                        channel=msg.channel,
                        pitch=msg.note,
                        velocity=velocity,
                        start_tick=start_tick,
                        end_tick=abs_tick,
                        start_time=start_time,
                        end_time=msg_time,
                        pitch_bend=list(pitch_bends.get(msg.channel, []))
                    )
                    track_notes.append(note)

            elif msg.type == 'pitchwheel':
                ch = msg.channel
                if ch not in pitch_bends:
                    pitch_bends[ch] = []
                semitones = (msg.pitch / 8192) * 2  # ±2 semitones default range
                pitch_bends[ch].append((msg_time, semitones))

        # Close any unclosed notes
        for key, (start_tick, velocity) in active_notes.items():
            ch, pitch = key
            note = Note(
                track_idx=trk_idx, channel=ch, pitch=pitch,
                velocity=velocity, start_tick=start_tick, end_tick=abs_tick,
                start_time=tick_to_time(start_tick), end_time=tick_to_time(abs_tick),
            )
            track_notes.append(note)

        if track_notes:
            if not track_name:
                track_name = f"Track {trk_idx + 1}"
            pitches = [n.pitch for n in track_notes]
            is_drum = any(n.is_drum for n in track_notes)
            track_infos.append(TrackInfo(
                index=trk_idx,
                name=track_name,
                channel=track_channel,
                color_idx=color_idx,
                note_count=len(track_notes),
                min_pitch=min(pitches),
                max_pitch=max(pitches),
                is_drum=is_drum,
            ))
            color_idx += 1
            notes.extend(track_notes)

    # Sort notes by start time
    notes.sort(key=lambda n: n.start_time)

    total_ticks = max((n.end_tick for n in notes), default=0)
    total_time = max((n.end_time for n in notes), default=0.0)
    all_pitches = [n.pitch for n in notes] if notes else [60]

    song_name = os.path.splitext(os.path.basename(filepath))[0]
    # Try to get song name from track 0
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'track_name' and msg.name:
                song_name = msg.name
                break
        break

    return MidiData(
        filename=filepath,
        song_name=song_name,
        ticks_per_beat=mid.ticks_per_beat,
        total_ticks=total_ticks,
        total_time=total_time,
        initial_bpm=tempo_changes[0].bpm,
        key_signature=key_sig,
        notes=notes,
        tracks=track_infos,
        tempo_changes=tempo_changes,
        time_signatures=time_sigs,
        min_pitch=min(all_pitches),
        max_pitch=max(all_pitches),
    )


# ---------------------------------------------------------------------------
# Multi-MIDI Project
# ---------------------------------------------------------------------------

@dataclass
class LoadedMidi:
    """A loaded MIDI instance within a multi-MIDI project."""
    id: str
    filepath: str
    filename: str
    data: MidiData
    color: tuple[int, int, int]
    track_colors: dict[int, tuple[int, int, int]] = field(default_factory=dict)
    custom_name: Optional[str] = None
    custom_track_names: dict[int, str] = field(default_factory=dict)
    time_offset: float = 0.0
    visible: bool = True

    @property
    def display_name(self) -> str:
        return self.custom_name if self.custom_name else self.filename

    def get_track_name(self, track_idx: int) -> str:
        if track_idx in self.custom_track_names and self.custom_track_names[track_idx]:
            return self.custom_track_names[track_idx]
        if self.custom_name:
            if len(self.data.tracks) <= 1 or track_idx == 0:
                return self.custom_name
            for t in self.data.tracks:
                if t.index == track_idx and t.name and t.name != f"Track {track_idx + 1}":
                    return f"{self.custom_name}: {t.name}"
            return f"{self.custom_name} #{track_idx + 1}"
        for t in self.data.tracks:
            if t.index == track_idx and t.name:
                return t.name
        return f"Track {track_idx + 1}"


class MultiMidiProject:
    """Manages multiple loaded MIDI files simultaneously."""

    def __init__(self):
        self._midis: list[LoadedMidi] = []
        self._counter: int = 0
        self.custom_song_name: Optional[str] = None
        self.custom_bpm: Optional[float] = None
        self.custom_key: Optional[str] = None

    @property
    def midis(self) -> list[LoadedMidi]:
        return self._midis

    def add_midi(self, filepath: str, color: Optional[tuple[int, int, int]] = None) -> LoadedMidi:
        """Parse and add a MIDI file to the project."""
        self._counter += 1
        midi_id = f"midi_{self._counter}"
        data = parse_midi(filepath)

        # Pick default color if none provided
        palette_defaults = [
            (0, 230, 210),   # cyan
            (255, 120, 50),  # orange
            (180, 130, 255), # lavender
            (255, 80, 120),  # coral
            (100, 255, 150), # mint
            (255, 220, 60),  # yellow
            (80, 180, 255),  # blue
        ]
        chosen_color = color or palette_defaults[(len(self._midis)) % len(palette_defaults)]

        # Tag notes with midi_id
        for n in data.notes:
            n.midi_id = midi_id

        loaded = LoadedMidi(
            id=midi_id,
            filepath=filepath,
            filename=os.path.basename(filepath),
            data=data,
            color=chosen_color,
            custom_name=os.path.splitext(os.path.basename(filepath))[0] if os.path.basename(filepath) else None,
        )
        if len(data.tracks) == 1 and loaded.custom_name:
            loaded.custom_track_names[data.tracks[0].index] = loaded.custom_name
        self._midis.append(loaded)
        return loaded

    def remove_midi(self, midi_id: str):
        """Remove a MIDI file by ID."""
        self._midis = [m for m in self._midis if m.id != midi_id]

    def clear(self):
        self._midis.clear()
        self._counter = 0

    def get_midi(self, midi_id: str) -> Optional[LoadedMidi]:
        for m in self._midis:
            if m.id == midi_id:
                return m
        return None

    def set_midi_color(self, midi_id: str, color: tuple[int, int, int]):
        m = self.get_midi(midi_id)
        if m:
            m.color = color

    def set_track_color(self, midi_id: str, track_idx: int, color: tuple[int, int, int]):
        m = self.get_midi(midi_id)
        if m:
            m.track_colors[track_idx] = color

    def set_midi_name(self, midi_id: str, new_name: str):
        m = self.get_midi(midi_id)
        if m:
            clean = new_name.strip()
            m.custom_name = clean
            if m.data.tracks:
                m.custom_track_names[m.data.tracks[0].index] = clean

    def set_track_name(self, midi_id: str, track_idx: int, new_name: str):
        m = self.get_midi(midi_id)
        if m:
            m.custom_track_names[track_idx] = new_name.strip()

    @property
    def total_time(self) -> float:
        if not self._midis:
            return 0.0
        return max(
            (m.data.total_time + m.time_offset for m in self._midis if m.visible),
            default=0.0
        )

    @property
    def min_pitch(self) -> int:
        visible = [m for m in self._midis if m.visible]
        if not visible:
            return 36
        return min((m.data.min_pitch for m in visible), default=36)

    @property
    def max_pitch(self) -> int:
        visible = [m for m in self._midis if m.visible]
        if not visible:
            return 84
        return max((m.data.max_pitch for m in visible), default=84)

    @property
    def initial_bpm(self) -> float:
        if self.custom_bpm is not None:
            return self.custom_bpm
        return self._midis[0].data.initial_bpm if self._midis else 120.0

    @property
    def key_signature(self) -> str:
        if self.custom_key is not None:
            return self.custom_key
        return self._midis[0].data.key_signature if self._midis else "C"

    @property
    def song_name(self) -> str:
        if self.custom_song_name is not None and self.custom_song_name.strip():
            return self.custom_song_name.strip()
        if not self._midis:
            return "Ethereal"
        if len(self._midis) == 1:
            return self._midis[0].display_name
        return f"{self._midis[0].display_name} + {len(self._midis)-1} tracks"

    def get_all_notes(self) -> list[Note]:
        """Aggregate all visible notes with applied time offsets and resolved colors."""
        all_notes: list[Note] = []
        for m in self._midis:
            if not m.visible:
                continue
            offset = m.time_offset
            for n in m.data.notes:
                # Track level check
                track_info = next((t for t in m.data.tracks if t.index == n.track_idx), None)
                if track_info and not track_info.visible:
                    continue

                # Resolve color override
                color = m.track_colors.get(n.track_idx, m.color)

                if offset != 0.0:
                    adjusted_note = Note(
                        track_idx=n.track_idx,
                        channel=n.channel,
                        pitch=n.pitch,
                        velocity=n.velocity,
                        start_tick=n.start_tick,
                        end_tick=n.end_tick,
                        start_time=n.start_time + offset,
                        end_time=n.end_time + offset,
                        pitch_bend=n.pitch_bend,
                        midi_id=m.id,
                        color_override=color
                    )
                    all_notes.append(adjusted_note)
                else:
                    n.color_override = color
                    all_notes.append(n)

        all_notes.sort(key=lambda x: x.start_time)
        return all_notes

