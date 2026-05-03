# Test Audio Sources

This file documents the provenance, license, and properties of every audio
fixture in `tests/audio/`. Add a new entry whenever a new file is added.

---

## zh_short.wav

| Property | Value |
|----------|-------|
| Duration | ~6.8 s |
| Format | 16 kHz, 16-bit PCM, mono WAV |
| Language | Mandarin Chinese (zh) |
| Speakers | 1 |
| Size | ~211 KB |

**Source**: Derived from `basic_ref_zh.wav` bundled with the
[F5-TTS](https://github.com/SWivid/F5-TTS) package
(`f5_tts/infer/examples/basic/basic_ref_zh.wav`), which in turn originates
from the [Seed-TTS evaluation set](https://arxiv.org/abs/2406.02430)
published by ByteDance.

**License**: The F5-TTS package is MIT licensed. The Seed-TTS reference audio
clips are distributed as part of the public evaluation benchmark. This
short clip is used solely for non-commercial automated testing.

**Processing**: Resampled to 16 kHz mono via ffmpeg.

**Purpose**: `zh_short.wav` is the primary Chinese-language fixture. It is
long enough (>5 s) to pass the LID minimum window (`LID_MIN_AUDIO_DURATION_S`
= 5.0) and is reliably classified as `zh` by whisper-tiny-mlx
(confidence ~0.98 in practice).

---

## zh_two_speakers.wav

| Property | Value |
|----------|-------|
| Duration | ~12.9 s |
| Format | 16 kHz, 16-bit PCM, mono WAV |
| Language | Mandarin Chinese (zh) |
| Speakers | 2 (simulated via pitch shift) |
| Size | ~403 KB |

**Source**: Synthetically derived from `zh_short.wav`.

**Construction**:
1. **Speaker 1** — `zh_short.wav` as-is, followed by 0.5 s of silence.
2. **Speaker 2** — `zh_short.wav` with a 20 % pitch increase
   (`asetrate=16000*1.2, aresample=16000`) to acoustically differentiate
   from speaker 1.
3. Segments are concatenated with ffmpeg's `concat` audio filter.

**License**: Derived from `zh_short.wav` — same MIT / Seed-TTS terms.

**Purpose**: Provides a two-speaker Chinese-language test fixture for
Sortformer diarization + Qwen3-ASR + ForcedAligner integration tests.
The pitch-shift creates enough spectral difference for Sortformer to
detect two speakers without requiring real multi-speaker recordings.

---

## longform_ep64_gay_talese.mp3

| Property | Value |
|----------|-------|
| Duration | ~82 min |
| Format | MP3 |
| Language | English |
| Speakers | 3 |
| Size | ~74.5 MB |

**Source**: [Longform Podcast Episode 64 — Gay Talese](https://archive.org/download/longform-podcast/2013-10-17%20Episode%2064%20Gay%20Talese.mp3)
via the Internet Archive.

**License**: Public domain / freely redistributable via Internet Archive.

**Purpose**: Long-audio regression test for Sortformer streaming OOM fix.
This file is NOT committed to git (too large). It is downloaded on demand
by `test_diarize_long_audio_streaming()` from archive.org and optionally
cached locally.

---

## voxceleb/

VoxCeleb speaker identification samples. See `voxceleb/README.md` if present.

---

## Files committed to git

Only the following small files are committed:

- `zh_short.wav` (~211 KB)
- `zh_two_speakers.wav` (~403 KB)

All other files (`*.mp3`, larger `*.wav`) are gitignored unless explicitly
excepted (see `.gitignore`).
