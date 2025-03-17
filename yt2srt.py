#!/usr/bin/env python3
"""
yt2srt.py - Audio/Video to SRT Transcription Tool

This script transcribes audio to an SRT subtitle file using the lightning-whisper-mlx library.
It can process YouTube videos, local audio files, or local video files.

Usage:
    python yt2srt.py [options] <input>

Where <input> can be:
    - YouTube URL
    - YouTube video ID (11 characters)
    - Path to local audio/video file

Examples:
    python yt2srt.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
    python yt2srt.py dQw4w9WgXcQ --model medium
    python yt2srt.py my_video.mp4 --model tiny --quantized 8bit
    python yt2srt.py podcast.mp3 --model distil-medium.en

The script can also be imported and used by other Python projects.
"""

import os
import re
import sys
import time
import json
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, List
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "large-v3"
AUDIO_SAMPLE_RATE = 16000  # 16kHz as required by Whisper
SUPPORTED_MODELS = [
    "tiny", "small", "base", "medium", "large", "large-v2", "large-v3",
    "distil-small.en", "distil-medium.en", "distil-large-v2", "distil-large-v3"
]
QUANTIZABLE_MODELS = [
    "tiny", "small", "base", "medium", "large", "large-v2", "large-v3"
]
MODELS_DIR = "mlx_models"  # Directory to store downloaded models
DEFAULT_BATCH_SIZE = 12
MAX_AUDIO_DURATION = 600  # Maximum audio duration in seconds before chunking (10 minutes)
CHUNK_DURATION = 300      # Target chunk duration in seconds (5 minutes)
MIN_SILENCE_LENGTH = 1.0  # Minimum silence length to split on (seconds)
SILENCE_THRESHOLD = -30   # dB threshold for silence detection


def extract_video_id(url_or_id: str) -> str:
    """
    Extract the YouTube video ID from a URL or return the ID if already provided.
    
    Args:
        url_or_id: YouTube URL or video ID
        
    Returns:
        The YouTube video ID
    """
    # YouTube ID pattern
    youtube_id_pattern = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    
    # Check if it's already just an ID (11 characters)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Try to extract ID from URL
    match = re.search(youtube_id_pattern, url_or_id)
    if match:
        return match.group(1)
    
    raise ValueError(f"Could not extract YouTube video ID from: {url_or_id}")


def download_youtube_audio(url_or_id: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
    """
    Download audio from a YouTube video.
    
    Args:
        url_or_id: YouTube URL or video ID
        output_dir: Directory to save the downloaded audio (default: temporary directory)
        
    Returns:
        Tuple containing (audio_file_path, video_title)
    """
    # Import yt-dlp here to allow the module to be imported even if yt-dlp is not installed
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp is required. Install it with: pip install yt-dlp")
        raise
    
    video_id = extract_video_id(url_or_id)
    
    # Use temporary directory if none specified
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare output filename template
    output_template = os.path.join(output_dir, f"{video_id}.%(ext)s")
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'extractaudio': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    logger.info(f"Downloading audio from YouTube video: {video_id}")
    
    # Download the audio
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
        video_title = info.get('title', video_id)
    
    # The downloaded file path
    audio_file = os.path.join(output_dir, f"{video_id}.mp3")
    
    if not os.path.exists(audio_file):
        raise FileNotFoundError(f"Failed to download audio file: {audio_file}")
    
    logger.info(f"Successfully downloaded audio to: {audio_file}")
    return audio_file, video_title


def convert_audio_for_whisper(input_file: str, output_dir: Optional[str] = None) -> str:
    """
    Convert audio file to the format required by Whisper (16kHz, mono, WAV).
    
    Args:
        input_file: Path to the input audio file
        output_dir: Directory to save the converted audio (default: same as input file)
        
    Returns:
        Path to the converted audio file
    """
    if output_dir is None:
        output_dir = os.path.dirname(input_file)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(output_dir, f"{base_name}_whisper.wav")
    
    # FFmpeg command to convert to 16kHz mono WAV
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-i", input_file,
        "-ar", str(AUDIO_SAMPLE_RATE),  # 16kHz sample rate
        "-ac", "1",  # Mono
        "-c:a", "pcm_s16le",  # 16-bit PCM
        output_file
    ]
    
    logger.info(f"Converting audio to Whisper format: {output_file}")
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise
    
    if not os.path.exists(output_file):
        raise FileNotFoundError(f"Failed to convert audio file: {output_file}")
    
    logger.info(f"Successfully converted audio to: {output_file}")
    return output_file


def get_audio_duration(file_path: str) -> float:
    """Get audio duration using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        file_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error getting duration: {e}")
        return 0.0


def detect_silences(audio_file: str, threshold: int = SILENCE_THRESHOLD, 
                    min_silence_len: float = MIN_SILENCE_LENGTH) -> List[Dict]:
    """
    Detect silences in audio file using ffmpeg silencedetect filter.
    
    Args:
        audio_file: Path to audio file
        threshold: Silence threshold in dB (default: -30dB)
        min_silence_len: Minimum silence length in seconds (default: 1.0s)
        
    Returns:
        List of silences with start and end times
    """
    cmd = [
        "ffmpeg",
        "-i", audio_file,
        "-af", f"silencedetect=noise={threshold}dB:d={min_silence_len}",
        "-f", "null",
        "-"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stderr  # ffmpeg outputs to stderr
        
        # Parse silence detection output
        silence_starts = re.findall(r"silence_start: (\d+\.?\d*)", output)
        silence_ends = re.findall(r"silence_end: (\d+\.?\d*)", output)
        
        silences = []
        for i in range(min(len(silence_starts), len(silence_ends))):
            silences.append({
                "start": float(silence_starts[i]),
                "end": float(silence_ends[i]),
                "duration": float(silence_ends[i]) - float(silence_starts[i])
            })
        
        logger.info(f"Detected {len(silences)} silence regions in audio")
        return silences
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error detecting silences: {e.stderr.decode() if e.stderr else str(e)}")
        return []


def split_audio_at_silences(audio_file: str, output_dir: str, 
                            target_duration: int = CHUNK_DURATION) -> List[str]:
    """
    Split audio file at silence points into chunks of approximately target duration.
    
    Args:
        audio_file: Path to input audio file
        output_dir: Directory to save chunks
        target_duration: Target chunk duration in seconds (default: 5 minutes)
        
    Returns:
        List of paths to audio chunks
    """
    # Get audio duration
    duration = get_audio_duration(audio_file)
    
    # If duration is short enough, don't split
    if duration <= MAX_AUDIO_DURATION:
        logger.info(f"Audio duration ({duration:.2f}s) is below threshold for chunking")
        return [audio_file]
    
    # Detect silences
    silences = detect_silences(audio_file)
    
    if not silences:
        logger.warning("No silences detected for splitting, using regular time intervals")
        return split_audio_at_intervals(audio_file, output_dir, target_duration)
    
    # Calculate optimal split points
    split_points = [0.0]  # Start with beginning of file
    current_time = 0.0
    
    for silence in silences:
        # If we're within target duration of the last split and the silence is significant
        if silence["start"] - current_time >= target_duration * 0.5 and silence["duration"] >= MIN_SILENCE_LENGTH:
            # Use middle of silence as split point
            split_point = (silence["start"] + silence["end"]) / 2
            split_points.append(split_point)
            current_time = split_point
    
    split_points.append(duration)  # End with end of file
    
    # If we couldn't find enough split points, fall back to intervals
    if len(split_points) <= 2:
        logger.warning("Not enough suitable silence points found, using regular time intervals")
        return split_audio_at_intervals(audio_file, output_dir, target_duration)
    
    # Generate output chunks
    chunks = []
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    
    for i in range(len(split_points) - 1):
        start_time = split_points[i]
        end_time = split_points[i + 1]
        chunk_duration = end_time - start_time
        
        # Skip very short chunks
        if chunk_duration < 1.0:
            continue
        
        chunk_file = os.path.join(output_dir, f"{base_name}_chunk{i+1:03d}.wav")
        
        # Use ffmpeg to extract chunk
        cmd = [
            "ffmpeg",
            "-y",
            "-i", audio_file,
            "-ss", str(start_time),
            "-to", str(end_time),
            "-ar", str(AUDIO_SAMPLE_RATE),
            "-ac", "1",
            "-c:a", "pcm_s16le",
            chunk_file
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Created chunk {i+1}: {start_time:.2f}s - {end_time:.2f}s ({chunk_duration:.2f}s)")
            chunks.append(chunk_file)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating chunk {i+1}: {e.stderr.decode() if e.stderr else str(e)}")
    
    logger.info(f"Split audio into {len(chunks)} chunks")
    return chunks


def split_audio_at_intervals(audio_file: str, output_dir: str, 
                             chunk_duration: int = CHUNK_DURATION) -> List[str]:
    """
    Split audio file at regular intervals when silence detection fails.
    
    Args:
        audio_file: Path to input audio file
        output_dir: Directory to save chunks
        chunk_duration: Chunk duration in seconds (default: 5 minutes)
        
    Returns:
        List of paths to audio chunks
    """
    # Get audio duration
    duration = get_audio_duration(audio_file)
    
    # Calculate number of chunks
    num_chunks = max(1, int(duration / chunk_duration))
    
    # Generate output chunks
    chunks = []
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    
    for i in range(num_chunks):
        start_time = i * chunk_duration
        end_time = min((i + 1) * chunk_duration, duration)
        
        chunk_file = os.path.join(output_dir, f"{base_name}_chunk{i+1:03d}.wav")
        
        # Use ffmpeg to extract chunk
        cmd = [
            "ffmpeg",
            "-y",
            "-i", audio_file,
            "-ss", str(start_time),
            "-to", str(end_time),
            "-ar", str(AUDIO_SAMPLE_RATE),
            "-ac", "1",
            "-c:a", "pcm_s16le",
            chunk_file
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Created chunk {i+1}: {start_time:.2f}s - {end_time:.2f}s ({end_time-start_time:.2f}s)")
            chunks.append(chunk_file)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating chunk {i+1}: {e.stderr.decode() if e.stderr else str(e)}")
    
    logger.info(f"Split audio into {len(chunks)} chunks at regular intervals")
    return chunks


def merge_transcription_segments(segments_list: List[List], offsets: List[float]) -> List[Dict]:
    """
    Merge transcription segments from multiple chunks with proper time offsets.
    
    Args:
        segments_list: List of segment lists from different chunks
        offsets: Start time offset for each chunk in seconds
        
    Returns:
        Merged list of segments with corrected timestamps
    """
    merged_segments = []
    
    for chunk_idx, segments in enumerate(segments_list):
        offset = offsets[chunk_idx]
        
        for segment in segments:
            # Adjust timestamps with chunk offset
            if isinstance(segment, dict):
                merged_segments.append({
                    "start": segment["start"] + offset,
                    "end": segment["end"] + offset,
                    "text": segment["text"]
                })
            elif isinstance(segment, list):
                # For list format [start_frame, end_frame, text]
                start_frame, end_frame, text = segment
                start_time = start_frame * 0.02 + offset  # 20ms per frame
                end_time = end_frame * 0.02 + offset
                merged_segments.append({
                    "start": start_time,
                    "end": end_time,
                    "text": text
                })
    
    # Sort segments by start time
    merged_segments.sort(key=lambda x: x["start"])
    
    # Check for overlaps and fix them
    for i in range(1, len(merged_segments)):
        if merged_segments[i]["start"] < merged_segments[i-1]["end"]:
            # Set start time to end of previous segment
            merged_segments[i]["start"] = merged_segments[i-1]["end"]
    
    return merged_segments


def transcribe_to_srt(
    audio_file: str, 
    model_name: str = DEFAULT_MODEL, 
    output_dir: Optional[str] = None,
    video_title: Optional[str] = None,
    video_id: Optional[str] = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    quant: Optional[str] = None
) -> str:
    """
    Transcribe audio file to SRT format using lightning-whisper-mlx.
    For long audio files, automatically splits into chunks.
    
    Args:
        audio_file: Path to the audio file
        model_name: Whisper model name to use
        output_dir: Directory to save the SRT file (default: same as audio file)
        video_title: Title of the video (for naming the output file)
        video_id: YouTube video ID (for naming the output file)
        batch_size: Batch size for transcription (default: 12)
        quant: Quantization level ('4bit' or '8bit')
        
    Returns:
        Path to the generated SRT file
    """
    # Import lightning-whisper-mlx here to allow the module to be imported even if lightning-whisper-mlx is not installed
    try:
        from lightning_whisper_mlx import LightningWhisperMLX
    except ImportError:
        logger.error("lightning-whisper-mlx is required. Install it with: pip install lightning-whisper-mlx")
        raise
    
    if output_dir is None:
        output_dir = os.path.dirname(audio_file)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    if video_id and video_title:
        # Clean the title to make it filesystem-friendly
        clean_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
        output_file = os.path.join(output_dir, f"[{video_id}] {clean_title}.srt")
    else:
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}.srt")
    
    logger.info(f"Transcribing audio using model: {model_name}")
    start_time = time.time()
    
    # Initialize model
    model = LightningWhisperMLX(
        model=model_name,
        batch_size=batch_size,
        quant=quant
    )
    
    # Check if file needs to be chunked
    audio_duration = get_audio_duration(audio_file)
    logger.info(f"Audio duration: {audio_duration:.2f} seconds")
    
    if audio_duration > MAX_AUDIO_DURATION:
        logger.info(f"Audio is longer than {MAX_AUDIO_DURATION}s, splitting into chunks")
        
        with tempfile.TemporaryDirectory() as chunk_dir:
            # Split audio into chunks
            chunks = split_audio_at_silences(audio_file, chunk_dir)
            
            # Transcribe each chunk
            all_segments = []
            offsets = []
            current_offset = 0.0
            
            for chunk_idx, chunk_file in enumerate(chunks):
                logger.info(f"Transcribing chunk {chunk_idx+1}/{len(chunks)}")
                chunk_result = model.transcribe(audio_path=chunk_file)
                all_segments.append(chunk_result["segments"])
                offsets.append(current_offset)
                
                # Update offset for next chunk
                chunk_duration = get_audio_duration(chunk_file)
                current_offset += chunk_duration
            
            # Merge segments with correct timing
            merged_segments = merge_transcription_segments(all_segments, offsets)
            result = {"segments": merged_segments, "text": " ".join(seg["text"] for seg in merged_segments)}
    else:
        # Transcribe as a single file
        result = model.transcribe(audio_path=audio_file)
    
    end_time = time.time()
    logger.info(f"Transcription completed in {end_time - start_time:.2f} seconds")
    
    # Convert the result to SRT format
    srt_content = segments_to_srt(result["segments"])
    
    # Write the SRT file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(srt_content)
    
    logger.info(f"SRT file saved to: {output_file}")
    return output_file


def segments_to_srt(segments: List) -> str:
    """
    Convert Whisper segments to SRT format.
    
    Args:
        segments: List of segments from Whisper transcription
        
    Returns:
        SRT formatted string
    """
    def format_timestamp(seconds: float) -> str:
        """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        seconds %= 3600
        minutes = int(seconds // 60)
        seconds %= 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    srt_lines = []
    
    for i, segment in enumerate(segments):
        # Handle different segment formats
        if isinstance(segment, list):
            # Format: [start_frame, end_frame, text]
            start_frame, end_frame, text = segment
            # Convert frames to seconds
            start_time = start_frame * 0.02  # 20ms per frame
            end_time = end_frame * 0.02
        elif isinstance(segment, dict):
            # Format: {"start": start_time, "end": end_time, "text": text}
            start_time = segment["start"]
            end_time = segment["end"]
            text = segment["text"]
        else:
            logger.warning(f"Unknown segment format: {segment}")
            continue
        
        # Format as SRT
        srt_lines.append(f"{i+1}")
        srt_lines.append(f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}")
        srt_lines.append(text.strip())
        
        # Add empty line between entries, but not after the last one
        if i < len(segments) - 1:
            srt_lines.append("")
    
    return "\n".join(srt_lines)


def process_input_file(input_file: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
    """
    Process an input audio/video file.
    
    Args:
        input_file: Path to the input audio/video file
        output_dir: Directory to save the processed audio (default: temporary directory)
        
    Returns:
        Tuple containing (audio_file_path, title)
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Use temporary directory if none specified
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract filename without extension as title
    title = os.path.splitext(os.path.basename(input_file))[0]
    
    # Convert to mp3 if not already
    if not input_file.lower().endswith('.mp3'):
        output_file = os.path.join(output_dir, f"{title}.mp3")
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", input_file,
            "-vn",  # Disable video
            "-acodec", "libmp3lame",
            "-q:a", "4",  # High quality
            output_file
        ]
        
        logger.info(f"Converting input file to mp3: {output_file}")
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
            raise
        
        audio_file = output_file
    else:
        audio_file = input_file
    
    return audio_file, title


def auto_detect_input(input_path: str) -> Tuple[str, bool]:
    """
    Auto-detect if the input is a YouTube URL, YouTube ID, or local file.
    
    Args:
        input_path: The input path or URL
        
    Returns:
        Tuple of (input_type, is_youtube) where:
        - input_type: 'youtube' or 'file'
        - is_youtube: True if it's a YouTube URL or ID
    """
    # Check if it's a YouTube URL
    youtube_url_pattern = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)'
    if re.search(youtube_url_pattern, input_path):
        logger.info(f"Detected YouTube URL: {input_path}")
        return 'youtube', True
    
    # Check if it's a YouTube ID (11 characters)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', input_path):
        logger.info(f"Detected YouTube ID: {input_path}")
        return 'youtube', True
    
    # Check if it's a local file
    if os.path.exists(input_path):
        logger.info(f"Detected local file: {input_path}")
        return 'file', False
    
    # If it's not a recognizable YouTube pattern and file doesn't exist
    # Check if it might be a relative path
    cwd_path = os.path.join(os.getcwd(), input_path)
    if os.path.exists(cwd_path):
        logger.info(f"Detected local file (relative path): {cwd_path}")
        return 'file', False
        
    # If nothing matches, assume it's a YouTube URL or ID that might be valid
    logger.warning(f"Could not definitively detect input type for '{input_path}'. Assuming YouTube ID/URL.")
    return 'youtube', True


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video files or YouTube videos to SRT format using lightning-whisper-mlx",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "input",
        help="Input source: YouTube URL, YouTube ID, or path to local audio/video file"
    )
    
    parser.add_argument(
        "--model",
        choices=SUPPORTED_MODELS,
        default=DEFAULT_MODEL,
        help="Whisper model to use for transcription"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default=os.getcwd(),
        help="Directory to save output files"
    )
    
    parser.add_argument(
        "--keep-audio", "-k",
        action="store_true",
        help="Keep downloaded and converted audio files"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Batch size for transcription"
    )
    
    parser.add_argument(
        "--quantized", "-q",
        choices=["4bit", "8bit"],
        help="Use quantized model (4bit or 8bit). Only available for non-distilled models."
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Auto-detect input type
    input_type, is_youtube = auto_detect_input(args.input)
    
    # Create temporary directory for audio files
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Process input source based on detected type
            if is_youtube:
                audio_file, title = download_youtube_audio(args.input, temp_dir if not args.keep_audio else args.output_dir)
                video_id = extract_video_id(args.input)
            else:
                audio_file, title = process_input_file(args.input, temp_dir if not args.keep_audio else args.output_dir)
                video_id = None
            
            # Convert audio to Whisper format
            whisper_audio = convert_audio_for_whisper(audio_file, temp_dir)
            
            # Transcribe
            srt_file = transcribe_to_srt(
                whisper_audio,
                args.model,
                args.output_dir,
                title,
                video_id,
                args.batch_size,
                args.quantized
            )
            
            logger.info(f"Transcription completed successfully. SRT file saved to: {srt_file}")
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    main() 