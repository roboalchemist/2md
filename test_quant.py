from lightning_whisper_mlx import LightningWhisperMLX

# Initialize model with 8-bit quantization
whisper = LightningWhisperMLX(model="tiny", batch_size=12, quant="8bit")

# Transcribe audio
result = whisper.transcribe("test_audio/test_voice.mp3")
print("\nTranscription result:")
print(result["text"]) 