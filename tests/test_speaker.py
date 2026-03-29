#!/usr/bin/env python3
"""
Tests for speaker.py — WeSpeaker ResNet293 speaker embedding extraction.

Run with: python -m pytest tests/test_speaker.py -v
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import numpy as np


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "audio" / "voxceleb"


def _fake_wespeaker_model(embedding_value: float = 0.5) -> MagicMock:
    """Return a mock wespeaker model that returns a fixed numpy embedding."""
    model = MagicMock()
    embedding = np.full(256, embedding_value, dtype=np.float32)
    model.extract_embedding.return_value = embedding
    return model


# ---------------------------------------------------------------------------
# Tests for _l2_normalize
# ---------------------------------------------------------------------------

class TestL2Normalize(unittest.TestCase):

    def test_normalizes_unit_vector(self):
        from any2md.speaker import _l2_normalize
        v = np.array([3.0, 4.0], dtype=np.float32)
        result = _l2_normalize(v)
        self.assertAlmostEqual(np.linalg.norm(result), 1.0, places=6)

    def test_returns_zeros_for_zero_vector(self):
        from any2md.speaker import _l2_normalize
        v = np.zeros(256, dtype=np.float32)
        result = _l2_normalize(v)
        # Zero vector stays zero — no division
        np.testing.assert_array_equal(result, v)

    def test_256d_random_vector_unit_after_normalize(self):
        from any2md.speaker import _l2_normalize
        rng = np.random.default_rng(42)
        v = rng.standard_normal(256).astype(np.float32)
        result = _l2_normalize(v)
        self.assertAlmostEqual(np.linalg.norm(result), 1.0, places=5)


# ---------------------------------------------------------------------------
# Tests for _import_wespeaker / _import_torch
# ---------------------------------------------------------------------------

class TestImportGuards(unittest.TestCase):

    @patch.dict("sys.modules", {"wespeaker": None})
    def test_import_wespeaker_missing_raises_clear_error(self):
        import importlib
        import any2md.speaker as spk
        importlib.reload(spk)
        with self.assertRaises(ImportError) as ctx:
            spk._import_wespeaker()
        self.assertIn("any2md[speaker]", str(ctx.exception))

    @patch.dict("sys.modules", {"torch": None})
    def test_import_torch_missing_raises_clear_error(self):
        import importlib
        import any2md.speaker as spk
        importlib.reload(spk)
        with self.assertRaises(ImportError) as ctx:
            spk._import_torch()
        self.assertIn("any2md[speaker]", str(ctx.exception))


# ---------------------------------------------------------------------------
# Tests for load_speaker_model
# ---------------------------------------------------------------------------

class TestLoadSpeakerModel(unittest.TestCase):

    def _mock_torch(self, mps_available: bool):
        torch_mock = MagicMock()
        torch_mock.backends.mps.is_available.return_value = mps_available
        return torch_mock

    @patch("any2md.speaker._import_wespeaker")
    @patch("any2md.speaker._import_torch")
    def test_loads_model_with_mps_when_available(self, mock_torch_fn, mock_ws_fn):
        torch_mock = self._mock_torch(mps_available=True)
        mock_torch_fn.return_value = torch_mock

        ws_mock = MagicMock()
        model_mock = MagicMock()
        ws_mock.load_model.return_value = model_mock
        mock_ws_fn.return_value = ws_mock

        from any2md.speaker import load_speaker_model
        result = load_speaker_model(device="mps")

        ws_mock.load_model.assert_called_once_with("english")
        model_mock.set_device.assert_called_once_with("mps")
        self.assertIs(result, model_mock)

    @patch("any2md.speaker._import_wespeaker")
    @patch("any2md.speaker._import_torch")
    def test_falls_back_to_cpu_when_mps_unavailable(self, mock_torch_fn, mock_ws_fn):
        torch_mock = self._mock_torch(mps_available=False)
        mock_torch_fn.return_value = torch_mock

        ws_mock = MagicMock()
        model_mock = MagicMock()
        ws_mock.load_model.return_value = model_mock
        mock_ws_fn.return_value = ws_mock

        from any2md.speaker import load_speaker_model
        result = load_speaker_model(device="mps")

        model_mock.set_device.assert_called_once_with("cpu")
        self.assertIs(result, model_mock)

    @patch("any2md.speaker._import_wespeaker")
    @patch("any2md.speaker._import_torch")
    def test_explicit_cpu_device(self, mock_torch_fn, mock_ws_fn):
        torch_mock = self._mock_torch(mps_available=True)
        mock_torch_fn.return_value = torch_mock

        ws_mock = MagicMock()
        model_mock = MagicMock()
        ws_mock.load_model.return_value = model_mock
        mock_ws_fn.return_value = ws_mock

        from any2md.speaker import load_speaker_model
        load_speaker_model(device="cpu")

        model_mock.set_device.assert_called_once_with("cpu")


# ---------------------------------------------------------------------------
# Tests for extract_embedding
# ---------------------------------------------------------------------------

class TestExtractEmbedding(unittest.TestCase):

    def test_raises_if_file_not_found(self):
        from any2md.speaker import extract_embedding
        model = _fake_wespeaker_model()
        with self.assertRaises(FileNotFoundError):
            extract_embedding(model, "/nonexistent/audio.wav")

    def test_returns_256d_float32_array(self):
        from any2md.speaker import extract_embedding
        model = _fake_wespeaker_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        try:
            result = extract_embedding(model, tmp)
            self.assertEqual(result.shape, (256,))
            self.assertEqual(result.dtype, np.float32)
        finally:
            os.unlink(tmp)

    def test_result_is_l2_normalized(self):
        from any2md.speaker import extract_embedding
        model = _fake_wespeaker_model(embedding_value=2.0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        try:
            result = extract_embedding(model, tmp)
            self.assertAlmostEqual(float(np.linalg.norm(result)), 1.0, places=5)
        finally:
            os.unlink(tmp)

    @patch("any2md.speaker._slice_audio_segment")
    def test_slices_segment_when_start_end_provided(self, mock_slice):
        from any2md.speaker import extract_embedding
        model = _fake_wespeaker_model()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = f.name
        try:
            result = extract_embedding(model, audio_path, start=1.0, end=3.5)
            # _slice_audio_segment should have been called with start/end
            mock_slice.assert_called_once()
            args = mock_slice.call_args[0]
            self.assertEqual(args[0], audio_path)
            self.assertAlmostEqual(args[1], 1.0)
            self.assertAlmostEqual(args[2], 3.5)
        finally:
            os.unlink(audio_path)

    def test_calls_model_directly_when_no_start_end(self):
        from any2md.speaker import extract_embedding
        model = _fake_wespeaker_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        try:
            extract_embedding(model, tmp)
            model.extract_embedding.assert_called_once_with(tmp)
        finally:
            os.unlink(tmp)

    def test_raises_value_error_if_start_geq_end(self):
        from any2md.speaker import extract_embedding
        model = _fake_wespeaker_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        try:
            with self.assertRaises(ValueError):
                extract_embedding(model, tmp, start=5.0, end=3.0)
        finally:
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# Tests for extract_embeddings_for_segments
# ---------------------------------------------------------------------------

class TestExtractEmbeddingsForSegments(unittest.TestCase):

    def _make_audio(self):
        """Create a temp WAV file and return its path."""
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        f.close()
        return f.name

    def test_raises_if_audio_not_found(self):
        from any2md.speaker import extract_embeddings_for_segments
        model = _fake_wespeaker_model()
        with self.assertRaises(FileNotFoundError):
            extract_embeddings_for_segments(model, "/no/such/file.wav", [])

    def test_empty_segments_returns_empty_list(self):
        from any2md.speaker import extract_embeddings_for_segments
        model = _fake_wespeaker_model()
        audio = self._make_audio()
        try:
            result = extract_embeddings_for_segments(model, audio, [])
            self.assertEqual(result, [])
        finally:
            os.unlink(audio)

    @patch("any2md.speaker._slice_audio_segment")
    def test_returns_one_dict_per_segment_with_embedding(self, mock_slice):
        from any2md.speaker import extract_embeddings_for_segments
        model = _fake_wespeaker_model()
        audio = self._make_audio()
        segments = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_0", "text": "Hello"},
            {"start": 2.5, "end": 5.0, "speaker": "SPEAKER_1", "text": "World"},
        ]
        try:
            results = extract_embeddings_for_segments(model, audio, segments)
            self.assertEqual(len(results), 2)
            for r, orig in zip(results, segments):
                # Original keys preserved
                self.assertEqual(r["start"], orig["start"])
                self.assertEqual(r["end"], orig["end"])
                self.assertEqual(r["speaker"], orig["speaker"])
                self.assertEqual(r["text"], orig["text"])
                # Embedding present and correct shape
                self.assertIn("embedding", r)
                self.assertEqual(r["embedding"].shape, (256,))
                self.assertEqual(r["embedding"].dtype, np.float32)
        finally:
            os.unlink(audio)

    @patch("any2md.speaker._slice_audio_segment")
    def test_embedding_is_l2_normalized(self, mock_slice):
        from any2md.speaker import extract_embeddings_for_segments
        model = _fake_wespeaker_model(embedding_value=3.0)
        audio = self._make_audio()
        segments = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_0"}]
        try:
            results = extract_embeddings_for_segments(model, audio, segments)
            norm = float(np.linalg.norm(results[0]["embedding"]))
            self.assertAlmostEqual(norm, 1.0, places=5)
        finally:
            os.unlink(audio)

    @patch("any2md.speaker._slice_audio_segment")
    def test_failed_segment_produces_zero_embedding(self, mock_slice):
        """If extract_embedding raises, the segment gets a zero vector instead of crashing."""
        from any2md.speaker import extract_embeddings_for_segments
        model = MagicMock()
        model.extract_embedding.side_effect = RuntimeError("model failure")
        audio = self._make_audio()
        segments = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_0"}]
        try:
            results = extract_embeddings_for_segments(model, audio, segments)
            self.assertEqual(len(results), 1)
            np.testing.assert_array_equal(results[0]["embedding"], np.zeros(256, dtype=np.float32))
        finally:
            os.unlink(audio)

    @patch("any2md.speaker._slice_audio_segment")
    def test_does_not_mutate_input_segments(self, mock_slice):
        """Input segment dicts must not be modified in-place."""
        from any2md.speaker import extract_embeddings_for_segments
        model = _fake_wespeaker_model()
        audio = self._make_audio()
        original = {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_0"}
        segments = [original]
        try:
            extract_embeddings_for_segments(model, audio, segments)
            # Original dict should not have 'embedding' key added
            self.assertNotIn("embedding", original)
        finally:
            os.unlink(audio)

    @patch("any2md.speaker._slice_audio_segment")
    def test_processes_all_speakers_sequentially(self, mock_slice):
        """All segments processed — no batching or skipping."""
        from any2md.speaker import extract_embeddings_for_segments
        model = _fake_wespeaker_model()
        audio = self._make_audio()
        segments = [
            {"start": float(i), "end": float(i + 1), "speaker": f"SPEAKER_{i}"}
            for i in range(5)
        ]
        try:
            results = extract_embeddings_for_segments(model, audio, segments)
            self.assertEqual(len(results), 5)
            # model.extract_embedding called once per segment (via _slice + tmp)
            self.assertEqual(model.extract_embedding.call_count, 5)
        finally:
            os.unlink(audio)


# ---------------------------------------------------------------------------
# Tests for _slice_audio_segment
# ---------------------------------------------------------------------------

class TestSliceAudioSegment(unittest.TestCase):

    def test_raises_value_error_for_invalid_range(self):
        from any2md.speaker import _slice_audio_segment
        with self.assertRaises(ValueError):
            _slice_audio_segment("/some/audio.wav", start=5.0, end=3.0, output_path="/tmp/out.wav")

    @patch("any2md.speaker.subprocess.run")
    def test_calls_ffmpeg_with_correct_args(self, mock_run):
        from any2md.speaker import _slice_audio_segment
        mock_run.return_value = MagicMock(returncode=0)
        _slice_audio_segment("/audio.wav", 1.0, 3.5, "/out.wav")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-ss", cmd)
        self.assertIn("1.0", cmd)
        self.assertIn("-to", cmd)
        self.assertIn("3.5", cmd)
        self.assertIn("/audio.wav", cmd)
        self.assertIn("/out.wav", cmd)


# ---------------------------------------------------------------------------
# Integration tests against real VoxCeleb fixtures
# (require actual files — skipped in CI unless fixtures exist)
# ---------------------------------------------------------------------------

@unittest.skipUnless(FIXTURES_DIR.exists(), "VoxCeleb fixtures not present")
class TestVoxCelebFixtures(unittest.TestCase):
    """Smoke-test shape/dtype of embeddings from real VoxCeleb WAV files."""

    def test_all_fixtures_produce_256d_embeddings(self):
        import any2md.speaker as spk

        torch_mock = MagicMock()
        torch_mock.backends.mps.is_available.return_value = False

        ws_mock = MagicMock()
        model_mock = _fake_wespeaker_model()
        ws_mock.load_model.return_value = model_mock

        with patch("any2md.speaker._import_wespeaker", return_value=ws_mock), \
             patch("any2md.speaker._import_torch", return_value=torch_mock):
            model = spk.load_speaker_model(device="cpu")

        wav_files = sorted(FIXTURES_DIR.rglob("*.wav"))
        self.assertGreater(len(wav_files), 0, "No WAV fixtures found under tests/audio/voxceleb/")

        for wav in wav_files:
            with self.subTest(wav=wav.name):
                emb = spk.extract_embedding(model, str(wav))
                self.assertEqual(emb.shape, (256,))
                self.assertEqual(emb.dtype, np.float32)
                norm = float(np.linalg.norm(emb))
                self.assertAlmostEqual(norm, 1.0, places=5)

    def test_segments_across_speakers(self):
        """Produce one embedding per VoxCeleb speaker using multi-segment path."""
        import any2md.speaker as spk

        torch_mock = MagicMock()
        torch_mock.backends.mps.is_available.return_value = False

        ws_mock = MagicMock()
        model_mock = _fake_wespeaker_model()
        ws_mock.load_model.return_value = model_mock

        with patch("any2md.speaker._import_wespeaker", return_value=ws_mock), \
             patch("any2md.speaker._import_torch", return_value=torch_mock):
            model = spk.load_speaker_model(device="cpu")

        # Build a fake segment list pointing at the first utterance of each speaker
        speakers = sorted(FIXTURES_DIR.iterdir())
        segments = []
        audio_paths = []
        for spk_dir in speakers:
            if not spk_dir.is_dir():
                continue
            wavs = sorted(spk_dir.glob("*.wav"))
            if wavs:
                audio_paths.append(str(wavs[0]))
                segments.append({
                    "start": 0.0, "end": 2.0,
                    "speaker": spk_dir.name,
                })

        if not audio_paths:
            self.skipTest("No WAV files found")

        # Use first audio file for all segments (mock slicing anyway)
        with patch("any2md.speaker._slice_audio_segment"):
            results = spk.extract_embeddings_for_segments(model, audio_paths[0], segments)

        self.assertEqual(len(results), len(segments))
        for r in results:
            self.assertIn("embedding", r)
            self.assertEqual(r["embedding"].shape, (256,))


if __name__ == "__main__":
    unittest.main()
