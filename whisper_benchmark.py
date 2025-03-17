#!/usr/bin/env python3
"""
Lightning Whisper MLX Benchmark

This script demonstrates how to use the lightning-whisper-mlx library for audio transcription
and benchmarks the performance of different models.

Usage:
    python whisper_benchmark.py

Author: Joseph Schlesinger
Date: March 13, 2024
"""

import os
import time
import logging
import argparse
import subprocess
from tabulate import tabulate
from lightning_whisper_mlx import LightningWhisperMLX

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define available models
AVAILABLE_MODELS = [
    "tiny",
    "small",
    "base",
    "medium",
    "large",
    "large-v2",
    "large-v3",
    "distil-small.en",
    "distil-medium.en",
    "distil-large-v2",
    "distil-large-v3"
]

def get_downloaded_models():
    """
    Get a list of models that have been downloaded to the mlx_models directory.
    
    Returns:
        list: List of downloaded model names
    """
    if not os.path.exists("mlx_models"):
        return []
    
    downloaded_models = []
    for model_name in AVAILABLE_MODELS:
        model_dir = os.path.join("mlx_models", model_name)
        if os.path.exists(model_dir) and os.path.isdir(model_dir):
            downloaded_models.append(model_name)
    
    return downloaded_models

def get_audio_duration(audio_path):
    """
    Get the duration of an audio file in seconds using ffprobe.
    
    Args:
        audio_path (str): Path to the audio file
        
    Returns:
        float: Duration of the audio file in seconds
    """
    try:
        result = subprocess.run(
            [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                audio_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10  # Add a timeout of 10 seconds
        )
        return float(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError) as e:
        logger.warning(f"Could not determine audio duration: {str(e)}")
        return None

def transcribe_audio(model_name, audio_path, batch_size=12, quant=None):
    """
    Transcribe an audio file using the specified model.
    
    Args:
        model_name (str): Name of the model to use
        audio_path (str): Path to the audio file
        batch_size (int): Batch size for transcription
        quant (str): Quantization type (None, "4bit", or "8bit")
        
    Returns:
        dict: Dictionary containing transcription results and timing information
    """
    logger.info(f"Transcribing with model: {model_name}, batch_size: {batch_size}, quant: {quant}")
    
    # Get audio duration
    audio_duration = get_audio_duration(audio_path)
    if audio_duration:
        logger.info(f"Audio duration: {audio_duration:.2f} seconds")
    
    # Initialize model
    start_time = time.time()
    try:
        whisper = LightningWhisperMLX(model=model_name, batch_size=batch_size, quant=quant)
        init_time = time.time() - start_time
        logger.info(f"Model initialization took {init_time:.2f} seconds")
        
        # Transcribe audio
        transcription_start = time.time()
        result = whisper.transcribe(audio_path=audio_path)
        transcription_time = time.time() - transcription_start
        
        logger.info(f"Transcription completed in {transcription_time:.2f} seconds")
        logger.info(f"Transcription result: {result['text'][:100]}...")
        
        # Calculate real-time factor
        realtime_factor = None
        if audio_duration:
            realtime_factor = transcription_time / audio_duration
            logger.info(f"Real-time factor: {realtime_factor:.2f}x (1/{1/realtime_factor:.2f} of real-time)")
        
        # Return results with timing information
        return {
            "model": model_name,
            "batch_size": batch_size,
            "quant": quant if quant else "None",
            "init_time": init_time,
            "transcription_time": transcription_time,
            "total_time": init_time + transcription_time,
            "audio_duration": audio_duration,
            "realtime_factor": realtime_factor,
            "text": result["text"],
            "segments": result.get("segments", [])
        }
    except Exception as e:
        logger.error(f"Error with model {model_name}: {str(e)}")
        return {
            "model": model_name,
            "batch_size": batch_size,
            "quant": quant if quant else "None",
            "init_time": time.time() - start_time,
            "transcription_time": None,
            "total_time": None,
            "audio_duration": audio_duration,
            "realtime_factor": None,
            "error": str(e)
        }

def run_benchmark(audio_path, models=None, batch_size=12):
    """
    Run a benchmark comparing different models.
    
    Args:
        audio_path (str): Path to the audio file
        models (list): List of models to benchmark
        batch_size (int): Batch size for transcription
        
    Returns:
        list: List of benchmark results
    """
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return []
    
    if models is None or len(models) == 0:
        # Auto-identify downloaded models
        models = get_downloaded_models()
        if not models:
            logger.warning("No models found in mlx_models directory. Using default models: tiny, small, medium")
            models = ["tiny", "small", "medium"]
    
    logger.info(f"Running benchmark with models: {models}")
    results = []
    
    # Run benchmark for each model
    for model in models:
        # Adjust batch size based on model size
        adjusted_batch_size = batch_size
        if "medium" in model:
            adjusted_batch_size = max(1, batch_size // 2)  # Reduce batch size for medium models
        elif "large" in model:
            adjusted_batch_size = max(1, batch_size // 4)  # Reduce batch size even more for large models
        
        # Run transcription
        result = transcribe_audio(model, audio_path, adjusted_batch_size)
        results.append(result)
        
        # Print a separator
        logger.info("-" * 80)
    
    return results

def display_results(results):
    """
    Display benchmark results in a table.
    
    Args:
        results (list): List of benchmark results
    """
    # Prepare table data
    table_data = []
    for result in results:
        if "error" in result:
            row = [
                result["model"],
                result["batch_size"],
                result["quant"],
                f"{result['init_time']:.2f}s" if result['init_time'] else "N/A",
                "Error",
                "Error",
                f"{result['audio_duration']:.2f}s" if result.get('audio_duration') else "N/A",
                "N/A",
                result["error"]
            ]
        else:
            realtime_info = "N/A"
            if result.get('realtime_factor'):
                realtime_info = f"{result['realtime_factor']:.2f}x (1/{1/result['realtime_factor']:.2f} real-time)"
            
            row = [
                result["model"],
                result["batch_size"],
                result["quant"],
                f"{result['init_time']:.2f}s",
                f"{result['transcription_time']:.2f}s",
                f"{result['total_time']:.2f}s",
                f"{result['audio_duration']:.2f}s" if result.get('audio_duration') else "N/A",
                realtime_info,
                result["text"][:50] + "..." if len(result["text"]) > 50 else result["text"]
            ]
        table_data.append(row)
    
    # Display table
    headers = ["Model", "Batch Size", "Quant", "Init Time", "Transcription Time", "Total Time", "Audio Duration", "Real-time Factor", "Result"]
    print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Find the fastest model
    valid_results = [r for r in results if "error" not in r]
    if valid_results:
        fastest = min(valid_results, key=lambda x: x["transcription_time"])
        print(f"\nFastest model: {fastest['model']} (batch_size: {fastest['batch_size']}, quant: {fastest['quant']})")
        print(f"Transcription time: {fastest['transcription_time']:.2f}s")
        if fastest.get('realtime_factor'):
            print(f"Real-time factor: {fastest['realtime_factor']:.2f}x (1/{1/fastest['realtime_factor']:.2f} of real-time)")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Lightning Whisper MLX Benchmark")
    parser.add_argument("--audio", default="test_audio/yt_video.mp3", help="Path to audio file")
    parser.add_argument("--models", nargs="+", choices=AVAILABLE_MODELS, 
                        help="Models to benchmark (if not specified, will use all downloaded models)")
    parser.add_argument("--batch-size", type=int, default=12, help="Base batch size")
    parser.add_argument("--simple", action="store_true", help="Run a simple transcription example")
    
    args = parser.parse_args()
    
    # Check if audio file exists
    if not os.path.exists(args.audio):
        logger.error(f"Audio file not found: {args.audio}")
        return
    
    # Print audio file information
    audio_size_mb = os.path.getsize(args.audio) / (1024 * 1024)
    logger.info(f"Audio file: {args.audio} ({audio_size_mb:.2f} MB)")
    
    if args.simple:
        # Simple example
        logger.info("Running simple transcription example with tiny model")
        result = transcribe_audio("tiny", args.audio)
        print("\nTranscription result:")
        print(result["text"])
        if result.get('realtime_factor'):
            print(f"\nReal-time factor: {result['realtime_factor']:.2f}x (1/{1/result['realtime_factor']:.2f} of real-time)")
    else:
        # Run benchmark
        results = run_benchmark(args.audio, args.models, args.batch_size)
        display_results(results)
        
        # Save the full transcription from the most accurate model
        if results and any("medium" in r["model"] or "large" in r["model"] for r in results if "error" not in r):
            accurate_models = [r for r in results if ("medium" in r["model"] or "large" in r["model"]) and "error" not in r]
            if accurate_models:
                with open("transcription_result.txt", "w") as f:
                    f.write(accurate_models[0]["text"])
                logger.info("Full transcription saved to transcription_result.txt")

if __name__ == "__main__":
    main() 