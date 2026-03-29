#!/usr/bin/env python3
"""
speaker.py - WeSpeaker ResNet293 speaker embedding extraction

Extracts 256-d L2-normalized speaker embeddings from audio segments using
WeSpeaker ResNet293 (Wespeaker/wespeaker-voxceleb-resnet293-LM) via PyTorch MPS
on Apple Silicon.

Usage (programmatic):
    from any2md.speaker import load_speaker_model, extract_embedding, extract_embeddings_for_segments

    model = load_speaker_model(device='mps')
    embedding = extract_embedding(model, 'audio.wav')  # (256,) numpy array
    results = extract_embeddings_for_segments(model, 'audio.wav', diarized_segments)
"""

import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# WeSpeaker model identifier used by wespeaker.load_model()
WESPEAKER_LANG = "english"  # downloads wespeaker-voxceleb-resnet293-LM

# Audio parameters — must match what WeSpeaker expects (same as Parakeet)
AUDIO_SAMPLE_RATE = 16000  # 16kHz mono WAV


def _import_wespeaker():
    """Import wespeaker, raising a clear error if not installed."""
    try:
        import wespeaker
        return wespeaker
    except ImportError as e:
        raise ImportError(
            "wespeaker not installed — run: uv pip install 'any2md[speaker]'"
        ) from e


def _import_torch():
    """Import torch, raising a clear error if not installed."""
    try:
        import torch
        return torch
    except ImportError as e:
        raise ImportError(
            "torch not installed — run: uv pip install 'any2md[speaker]'"
        ) from e


def load_speaker_model(device: str = "mps") -> Any:
    """Load WeSpeaker ResNet293 speaker embedding model.

    Downloads the model from HuggingFace on first call (cached afterwards).
    Uses PyTorch MPS on Apple Silicon; falls back to CPU if MPS is unavailable.

    Args:
        device: PyTorch device string. 'mps' for Apple Silicon (default),
                'cuda' for NVIDIA GPU, 'cpu' for CPU-only.

    Returns:
        Loaded WeSpeaker model object with set_device() already called.

    Raises:
        ImportError: If wespeaker or torch is not installed.
    """
    wespeaker = _import_wespeaker()
    torch = _import_torch()

    # Resolve device — fall back to CPU if MPS is requested but not available
    if device == "mps":
        if torch.backends.mps.is_available():
            resolved_device = "mps"
        else:
            logger.warning("MPS not available, falling back to CPU for speaker embeddings")
            resolved_device = "cpu"
    else:
        resolved_device = device

    logger.info("Loading WeSpeaker ResNet293 model (device=%s)...", resolved_device)
    model = wespeaker.load_model(WESPEAKER_LANG)
    model.set_device(resolved_device)
    logger.info("WeSpeaker model loaded successfully")
    return model


def _slice_audio_segment(
    audio_path: str,
    start: float,
    end: float,
    output_path: str,
) -> None:
    """Slice an audio segment using ffmpeg.

    Args:
        audio_path: Source WAV file path (16kHz mono WAV).
        start: Start time in seconds.
        end: End time in seconds.
        output_path: Destination WAV file path.

    Raises:
        subprocess.CalledProcessError: If ffmpeg fails.
        ValueError: If start >= end.
    """
    if start >= end:
        raise ValueError(f"Segment start ({start}) must be less than end ({end})")

    cmd = [
        "ffmpeg",
        "-y",           # Overwrite output
        "-ss", str(start),
        "-to", str(end),
        "-i", audio_path,
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path,
    ]

    logger.debug("Slicing audio: ffmpeg -ss %.3f -to %.3f ...", start, end)
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        raise subprocess.CalledProcessError(
            e.returncode, e.cmd,
            output=e.output,
            stderr=f"ffmpeg segment slice failed: {stderr}".encode(),
        )


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalize a 1-D numpy array in-place (returns new array)."""
    norm = np.linalg.norm(vec)
    if norm < 1e-10:
        return vec
    return vec / norm


def extract_embedding(
    model: Any,
    audio_path: str,
    start: Optional[float] = None,
    end: Optional[float] = None,
) -> np.ndarray:
    """Extract a 256-d L2-normalized speaker embedding from an audio file or segment.

    If start/end are provided, the segment is sliced via ffmpeg to a temp WAV
    before embedding extraction. If start/end are None, the full file is used.

    Args:
        model: Loaded WeSpeaker model (from load_speaker_model()).
        audio_path: Path to 16kHz mono WAV file.
        start: Segment start time in seconds (optional).
        end: Segment end time in seconds (optional).

    Returns:
        numpy.ndarray of shape (256,) and dtype float32, L2-normalized.

    Raises:
        ImportError: If wespeaker is not installed.
        FileNotFoundError: If audio_path does not exist.
        ValueError: If start >= end when both are provided.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if start is not None and end is not None:
        # Slice to a temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            _slice_audio_segment(audio_path, start, end, tmp_path)
            raw = model.extract_embedding(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    else:
        raw = model.extract_embedding(audio_path)

    # wespeaker returns a numpy array; ensure float32 and L2-normalize
    embedding = np.array(raw, dtype=np.float32).flatten()
    return _l2_normalize(embedding)


def extract_embeddings_for_segments(
    model: Any,
    audio_path: str,
    segments: List[Dict],
) -> List[Dict]:
    """Extract speaker embeddings for a list of diarized segments.

    Processes segments sequentially (not batched) to keep MPS memory usage
    predictable on Apple Silicon. Each segment is sliced to a temp WAV via
    ffmpeg and passed to WeSpeaker for embedding extraction.

    Args:
        model: Loaded WeSpeaker model (from load_speaker_model()).
        audio_path: Path to 16kHz mono WAV file (same file used for STT).
        segments: List of diarization segment dicts, each containing at minimum:
            - 'start': float, segment start time in seconds
            - 'end': float, segment end time in seconds
            - 'speaker': str, speaker label (e.g., 'SPEAKER_0')
            May also contain 'text' and other keys (passed through unchanged).

    Returns:
        List of dicts, one per input segment, with the original keys preserved
        plus 'embedding' (numpy.ndarray of shape (256,), float32, L2-normalized).
        Example item::

            {
                'start': 0.0,
                'end': 3.5,
                'speaker': 'SPEAKER_0',
                'text': 'Hello world',
                'embedding': np.array([...], dtype=float32),  # (256,)
            }

    Raises:
        ImportError: If wespeaker is not installed.
        FileNotFoundError: If audio_path does not exist.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    results = []
    for i, seg in enumerate(segments):
        start = float(seg["start"])
        end = float(seg["end"])
        speaker_id = seg.get("speaker", f"SPEAKER_{i}")

        logger.debug(
            "Extracting embedding for segment %d/%d: %s [%.2f-%.2f]",
            i + 1, len(segments), speaker_id, start, end,
        )

        try:
            embedding = extract_embedding(model, audio_path, start=start, end=end)
        except Exception as e:
            logger.warning(
                "Failed to extract embedding for segment %d (%s, %.2f-%.2f): %s",
                i, speaker_id, start, end, e,
            )
            embedding = np.zeros(256, dtype=np.float32)

        out = dict(seg)  # copy all original keys (start, end, speaker, text, ...)
        out["embedding"] = embedding
        results.append(out)

    logger.info("Extracted %d speaker embeddings from %s", len(results), audio_path)
    return results
