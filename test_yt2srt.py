#!/usr/bin/env python3
"""
Test script for yt2srt.py

This script tests the functionality of yt2srt.py by:
1. Testing the extract_video_id function with various inputs
2. Testing the segments_to_srt function with sample data
3. Optionally running a full integration test with a short YouTube video

Run with: python test_yt2srt.py
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import functions from yt2srt.py
try:
    from yt2srt import (
        extract_video_id,
        segments_to_srt,
        process_youtube_video,
    )
except ImportError as e:
    print(f"Error importing from yt2srt.py: {e}")
    print("Make sure yt2srt.py is in the same directory and all dependencies are installed.")
    print("Required packages: yt-dlp, lightning-whisper-mlx")
    sys.exit(1)


class TestYt2Srt(unittest.TestCase):
    """Test cases for yt2srt.py functions"""

    def test_extract_video_id(self):
        """Test the extract_video_id function with various inputs"""
        # Test with direct video ID
        self.assertEqual(extract_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        
        # Test with standard YouTube URL
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ"
        )
        
        # Test with shortened URL
        self.assertEqual(
            extract_video_id("https://youtu.be/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ"
        )
        
        # Test with URL containing additional parameters
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s"),
            "dQw4w9WgXcQ"
        )
        
        # Test with embedded URL
        self.assertEqual(
            extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ"
        )
        
        # Test with invalid input
        with self.assertRaises(ValueError):
            extract_video_id("not-a-youtube-url")

    def test_segments_to_srt(self):
        """Test the segments_to_srt function with sample data"""
        # Sample segments data in list format [start_frame, end_frame, text]
        segments = [
            [0, 125, "Hello, this is a test."],
            [125, 250, "Testing the SRT conversion."],
            [250, 500, "This should generate a valid SRT file."]
        ]
        
        # Expected SRT output - note that we don't include the final newline
        expected_srt = (
            "1\n"
            "00:00:00,000 --> 00:00:02,500\n"
            "Hello, this is a test.\n"
            "\n"
            "2\n"
            "00:00:02,500 --> 00:00:05,000\n"
            "Testing the SRT conversion.\n"
            "\n"
            "3\n"
            "00:00:05,000 --> 00:00:10,000\n"
            "This should generate a valid SRT file."
        )
        
        # Test the conversion
        self.assertEqual(segments_to_srt(segments), expected_srt)

    def test_segments_to_srt_dict_format(self):
        """Test the segments_to_srt function with dictionary format data"""
        # Sample segments data in dictionary format
        segments = [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "Hello, this is a test."
            },
            {
                "start": 2.5,
                "end": 5.0,
                "text": "Testing the SRT conversion."
            },
            {
                "start": 5.0,
                "end": 10.0,
                "text": "This should generate a valid SRT file."
            }
        ]
        
        # Expected SRT output - note that we don't include the final newline
        expected_srt = (
            "1\n"
            "00:00:00,000 --> 00:00:02,500\n"
            "Hello, this is a test.\n"
            "\n"
            "2\n"
            "00:00:02,500 --> 00:00:05,000\n"
            "Testing the SRT conversion.\n"
            "\n"
            "3\n"
            "00:00:05,000 --> 00:00:10,000\n"
            "This should generate a valid SRT file."
        )
        
        # Test the conversion
        self.assertEqual(segments_to_srt(segments), expected_srt)


def run_integration_test():
    """
    Run a full integration test with a short YouTube video.
    This is optional and will only run if explicitly requested.
    """
    # Check if required packages are installed
    try:
        import yt_dlp
    except ImportError:
        print("❌ Integration test skipped: yt-dlp is not installed.")
        print("Install it with: pip install yt-dlp")
        return False
    
    try:
        from lightning_whisper_mlx import transcribe_audio
    except ImportError:
        print("❌ Integration test skipped: lightning-whisper-mlx is not installed.")
        print("Install it with: pip install lightning-whisper-mlx")
        return False
    
    # Use a very short video for testing
    TEST_VIDEO_ID = "JMyzTkOLn0w"  # 5-second test video
    
    print(f"Running integration test with video ID: {TEST_VIDEO_ID}")
    
    # Create a temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Use the smallest model for faster testing
            srt_file = process_youtube_video(
                TEST_VIDEO_ID,
                model_name="tiny",
                output_dir=temp_dir,
                keep_audio=True
            )
            
            # Check if the SRT file was created
            if os.path.exists(srt_file):
                print(f"✅ Integration test passed! SRT file created: {srt_file}")
                
                # Print the content of the SRT file
                print("\nSRT file content:")
                with open(srt_file, "r", encoding="utf-8") as f:
                    print(f.read())
                
                return True
            else:
                print(f"❌ Integration test failed! SRT file not created: {srt_file}")
                return False
                
        except Exception as e:
            print(f"❌ Integration test failed with error: {str(e)}")
            return False


if __name__ == "__main__":
    # Run the unit tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    # Ask if the user wants to run the integration test
    print("\n=== Unit tests completed ===\n")
    
    choice = input("Do you want to run the integration test? This will download a short YouTube video and transcribe it. (y/n): ")
    
    if choice.lower() in ('y', 'yes'):
        run_integration_test()
    else:
        print("Integration test skipped.") 