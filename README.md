# Lightning Whisper MLX Benchmark

A comprehensive benchmark and example for using the [lightning-whisper-mlx](https://github.com/mustafaaljadery/lightning-whisper-mlx) library to transcribe audio files on Apple Silicon.

## Overview

The lightning-whisper-mlx library is an incredibly fast implementation of Whisper optimized for Apple Silicon. It provides:
- Batched decoding for higher throughput
- Distilled models for faster decoding
- Quantized models for faster memory movement

This benchmark script demonstrates how to use the library and compares the performance of different models, including real-time factors to show how much faster the transcription is compared to the actual audio duration.

## Prerequisites

- macOS running on Apple Silicon (M1/M2/M3)
- Python 3.8+
- pip
- ffmpeg/ffprobe (for audio duration calculation)

## Installation

1. Clone the lightning-whisper-mlx repository:
```bash
git clone https://github.com/mustafaaljadery/lightning-whisper-mlx.git
```

2. Install the lightning-whisper-mlx package:
```bash
cd lightning-whisper-mlx
pip install -e .
cd ..
```

3. Install additional dependencies:
```bash
pip install tabulate
```

4. Install ffmpeg/ffprobe (if not already installed):
```bash
# Using Homebrew
brew install ffmpeg
```

## Usage

### Simple Transcription

To run a simple transcription example:

```bash
python whisper_benchmark.py --simple --audio path/to/your/audio.mp3
```

This will transcribe the audio file using the "tiny" model and display the result along with the real-time factor.

### Benchmark

To benchmark multiple models:

```bash
python whisper_benchmark.py --models tiny small medium --audio path/to/your/audio.mp3
```

This will run a benchmark comparing the specified models and display the results in a table, including real-time factors.

### Command-line Arguments

- `--audio`: Path to the audio file (default: "test_audio/yt_video.mp3")
- `--models`: Models to benchmark (choices: tiny, small, base, medium, large, large-v2, large-v3, distil-small.en, distil-medium.en, distil-large-v2, distil-large-v3)
- `--batch-size`: Base batch size for transcription (default: 12)
- `--simple`: Run a simple transcription example instead of a benchmark

## Example Output

```
+----------+------------+-------+------------+--------------------+------------+------------------+---------------------------+----------------------------------------------------+
| Model    | Batch Size | Quant | Init Time  | Transcription Time | Total Time | Audio Duration   | Real-time Factor          | Result                                             |
+----------+------------+-------+------------+--------------------+------------+------------------+---------------------------+----------------------------------------------------+
| tiny     | 12         | None  | 0.24s      | 4.35s              | 4.59s      | 555.22s          | 0.01x (1/127.73 real-time)| This is a test of the speech recognition system... |
| small    | 12         | None  | 0.17s      | 20.28s             | 20.46s     | 555.22s          | 0.04x (1/27.37 real-time) | This is a test of the speech recognition system... |
| medium   | 6          | None  | 27.01s     | 91.65s             | 118.66s    | 555.22s          | 0.17x (1/6.06 real-time)  | This is a test of the speech recognition system... |
+----------+------------+-------+------------+--------------------+------------+------------------+---------------------------+----------------------------------------------------+

Fastest model: tiny (batch_size: 12, quant: None)
Transcription time: 4.35s
Real-time factor: 0.01x (1/127.73 of real-time)
```

## Performance Notes

- The "tiny" model is the fastest, processing audio at approximately 127x real-time speed
- The "small" model is slower but still very fast at approximately 27x real-time speed
- The "medium" model provides better accuracy while still processing at approximately 6x real-time speed
- Larger models require more memory, so the batch size is automatically reduced
- Model initialization time can be significant, especially for larger models
- For production use, you would typically initialize the model once and reuse it for multiple transcriptions

## Troubleshooting

- If you encounter memory issues, try reducing the batch size
- Quantized models (4-bit, 8-bit) may have compatibility issues with the current version of the library
- For long audio files, the transcription is automatically split into segments
- If ffprobe is not found, the real-time factor calculation will be skipped

## License

This benchmark script is provided under the same license as the lightning-whisper-mlx library.

# yt2srt - YouTube to SRT Transcription Tool

A command-line tool that downloads audio from YouTube videos and transcribes it to SRT subtitle files using the lightning-whisper-mlx library, which leverages Apple's MLX framework for efficient transcription on Apple Silicon devices.

## Features

- Downloads audio from YouTube videos using yt-dlp
- Converts audio to the optimal format for Whisper (16kHz, mono)
- Transcribes audio using lightning-whisper-mlx (OpenAI's Whisper model optimized for Apple Silicon)
- Generates SRT subtitle files with proper timestamps
- Supports various Whisper model sizes (tiny, base, small, medium, large-v2, large-v3)
- Can be used as a command-line tool or imported into other Python projects

## Requirements

- Python 3.8+
- Apple Silicon Mac (M1/M2/M3)
- FFmpeg (for audio conversion)
- Required Python packages:
  - lightning-whisper-mlx
  - yt-dlp

## Installation

1. Clone this repository or download the `yt2srt.py` file.

2. Install the required dependencies:

```bash
pip install lightning-whisper-mlx yt-dlp
```

3. Ensure FFmpeg is installed on your system:

```bash
# macOS (using Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

4. Make the script executable:

```bash
chmod +x yt2srt.py
```

## Usage

### Command Line

Basic usage:

```bash
python yt2srt.py <youtube_url_or_id>
```

Example:

```bash
python yt2srt.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

With options:

```bash
python yt2srt.py --model medium --output-dir ~/subtitles --keep-audio dQw4w9WgXcQ
```

### Options

- `youtube_url_or_id`: YouTube URL or video ID (required)
- `--model`: Whisper model to use (default: large-v3)
  - Choices: tiny, base, small, medium, large-v2, large-v3
- `--output-dir`, `-o`: Directory to save output files (default: current directory)
- `--keep-audio`, `-k`: Keep downloaded and converted audio files (default: False)
- `--verbose`, `-v`: Enable verbose output (default: False)

### As a Python Module

You can also import and use the tool in your Python projects:

```python
from yt2srt import process_youtube_video

# Process a YouTube video and get the path to the generated SRT file
srt_file = process_youtube_video(
    url_or_id="dQw4w9WgXcQ",
    model_name="large-v3",
    output_dir="~/subtitles",
    keep_audio=False
)

print(f"Generated SRT file: {srt_file}")
```

## Output

The tool generates:

1. An SRT file named `[video_id] video_title.srt` in the specified output directory
2. Temporary audio files (deleted by default unless `--keep-audio` is specified)

## Models

The tool supports the following Whisper models:

- `tiny`: Smallest model, fastest but least accurate
- `base`: Small model with reasonable accuracy
- `small`: Good balance between speed and accuracy
- `medium`: More accurate but slower
- `large-v2`: Very accurate but slower
- `large-v3`: Most accurate, latest model (default)

Models are downloaded from HuggingFace the first time they are used and cached locally in the `mlx_models` directory.

## License

MIT

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper)
- [lightning-whisper-mlx](https://github.com/ml-explore/mlx-examples/tree/main/whisper)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [MLX](https://github.com/ml-explore/mlx) 