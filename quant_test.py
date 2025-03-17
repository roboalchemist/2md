#!/usr/bin/env python3
"""
Quantization Test for Lightning Whisper MLX

This script tests different quantization options with the lightning-whisper-mlx library.
First runs a warm-up with test_voice.mp3, then benchmarks with yt_video.mp3.
"""

import os
import time
import logging
from lightning_whisper_mlx import LightningWhisperMLX, transcribe_audio
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_model(model_name, quant_bits=None, audio_path="test_audio/test_voice.mp3", is_warmup=False):
    try:
        prefix = "[WARMUP] " if is_warmup else ""
        print(f"{prefix}Testing model: {model_name} with {quant_bits if quant_bits else 'no'} quantization")
        
        # Check if model files exist locally first
        model_dir = os.path.join("mlx_models", model_name)
        model_exists = os.path.exists(model_dir) and os.path.exists(os.path.join(model_dir, "weights.npz"))
        
        if not model_exists:
            print(f"Warning: Model files not found locally at {model_dir}, will download from HuggingFace")
            path_or_hf_repo = f"mlx-community/whisper-{model_name}-mlx"
        else:
            print(f"Using locally cached model at {model_dir}")
            path_or_hf_repo = model_dir
            
        # Adjust batch size for large models
        batch_size = 4 if "large" in model_name else 6
        print(f"{prefix}Using batch size: {batch_size}")
        
        # Convert quantization format
        quant = f"{quant_bits}bit" if quant_bits else None
        
        # Transcribe audio
        start_time = time.time()
        result = transcribe_audio(
            audio_path,
            path_or_hf_repo=path_or_hf_repo,
            batch_size=batch_size,
            fp16=(quant is None),  # Use fp16 for non-quantized models
            verbose=True
        )
        end_time = time.time()
        
        print(f"{prefix}Transcription completed in {end_time - start_time:.2f} seconds")
        print(f"{prefix}Result: {result['text']}")
        print("-" * 80)
        
        return True
    except Exception as e:
        print(f"{prefix}Error testing {model_name}: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Main function to test different quantization options."""
    # Models to test
    models_to_test = [
        ("large-v3", None),  # No quantization
        ("large-v3", 4),     # 4-bit quantization
        ("large-v3", 8),     # 8-bit quantization
    ]
    
    # First do a warmup run with test_voice.mp3
    print("Starting warmup phase...")
    for model_name, quant_bits in models_to_test:
        test_model(model_name, quant_bits, audio_path="test_audio/test_voice.mp3", is_warmup=True)
    
    print("\nStarting main benchmark phase...")
    # Then do the main benchmark with yt_video.mp3
    for model_name, quant_bits in models_to_test:
        test_model(model_name, quant_bits, audio_path="test_audio/yt_video.mp3", is_warmup=False)

if __name__ == "__main__":
    main()