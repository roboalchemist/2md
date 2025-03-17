#!/usr/bin/env python3
"""
Download all available models for lightning-whisper-mlx

This script downloads all available models for the lightning-whisper-mlx library
to the mlx_models directory.

Usage:
    python download_models.py

Author: Joseph Schlesinger
Date: March 13, 2024
"""

import os
import time
import logging
from lightning_whisper_mlx import LightningWhisperMLX

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define all available models
MODELS = [
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

def download_model(model_name):
    """
    Download a model to the mlx_models directory.
    
    Args:
        model_name (str): Name of the model to download
    """
    logger.info(f"Downloading model: {model_name}")
    
    # Check if model is already downloaded
    model_dir = os.path.join("mlx_models", model_name)
    if os.path.exists(model_dir) and os.path.isdir(model_dir):
        logger.info(f"Model {model_name} is already downloaded at {model_dir}")
        return
    
    # Initialize model (this will download the model)
    start_time = time.time()
    try:
        # Set a small batch size to minimize memory usage during download
        batch_size = 1
        whisper = LightningWhisperMLX(model=model_name, batch_size=batch_size, quant=None)
        download_time = time.time() - start_time
        logger.info(f"Model {model_name} downloaded in {download_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error downloading model {model_name}: {str(e)}")

def main():
    """Main function."""
    logger.info(f"Downloading {len(MODELS)} models to mlx_models directory")
    
    # Create mlx_models directory if it doesn't exist
    os.makedirs("mlx_models", exist_ok=True)
    
    # Download each model
    for model in MODELS:
        download_model(model)
        logger.info("-" * 80)
    
    logger.info("All models downloaded successfully")

if __name__ == "__main__":
    main() 