import unittest
import os
import sys
import tempfile
import subprocess
import json
from pathlib import Path

class TestWhisperBenchmark(unittest.TestCase):
    def setUp(self):
        # Ensure the test audio file exists
        self.test_audio_file = "test_voice.mp3"
        self.assertTrue(os.path.exists(self.test_audio_file), f"Test audio file {self.test_audio_file} not found")
        
        # Ensure the benchmark script exists
        self.benchmark_script = "whisper_benchmark.py"
        self.assertTrue(os.path.exists(self.benchmark_script), f"Benchmark script {self.benchmark_script} not found")
        
        # Ensure at least one model is downloaded
        self.model_dir = Path("mlx_models")
        self.assertTrue(self.model_dir.exists(), "Model directory not found")
        
        # Check if at least one model is available
        models = [d for d in self.model_dir.iterdir() if d.is_dir()]
        self.assertTrue(len(models) > 0, "No models found in the model directory")
        
        # Use the tiny model for testing as it's the fastest
        self.test_model = "tiny"
        self.assertTrue((self.model_dir / self.test_model).exists(), 
                        f"Test model {self.test_model} not found in {self.model_dir}")

    def test_benchmark_script_runs(self):
        """Test that the benchmark script runs without errors."""
        result = subprocess.run(
            [sys.executable, self.benchmark_script, "--audio", self.test_audio_file, "--models", self.test_model],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        self.assertEqual(result.returncode, 0, f"Benchmark script failed with error: {result.stderr}")
        
        # Check for the table output which indicates successful completion
        self.assertIn("| Model", result.stdout, "Model table header not found in output")
        self.assertIn("| tiny", result.stdout, "Tiny model not found in output table")
        self.assertIn("Real-time Factor", result.stdout, "Real-time factor not reported")
        self.assertIn("Fastest model:", result.stdout, "Fastest model summary not found")

    def test_auto_model_detection(self):
        """Test that the script auto-detects models when none are specified."""
        result = subprocess.run(
            [sys.executable, self.benchmark_script, "--audio", self.test_audio_file],
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        self.assertEqual(result.returncode, 0, f"Benchmark script failed with error: {result.stderr}")
        
        # Check that multiple models appear in the output table
        model_count = result.stdout.count("| ")
        # Each model should have at least one line in the table, plus header and separator lines
        self.assertGreater(model_count, 3, "Not enough models detected automatically")
        
        # Check that the fastest model summary is present
        self.assertIn("Fastest model:", result.stdout, "Fastest model summary not found")

    def test_transcription_result_file(self):
        """Test that the transcription result is saved to a file."""
        # First, run the benchmark
        result = subprocess.run(
            [sys.executable, self.benchmark_script, "--audio", self.test_audio_file, "--models", self.test_model],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        self.assertEqual(result.returncode, 0, f"Benchmark script failed with error: {result.stderr}")
        
        # Check that the transcription result file exists
        result_file = "transcription_result.txt"
        self.assertTrue(os.path.exists(result_file), f"Transcription result file {result_file} not found")
        
        # Check that the file is not empty
        with open(result_file, 'r') as f:
            content = f.read()
        self.assertTrue(len(content) > 0, "Transcription result file is empty")

if __name__ == "__main__":
    unittest.main() 