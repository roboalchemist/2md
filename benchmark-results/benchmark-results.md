# Lightning Whisper MLX Benchmark Results

## Test Configuration
- Audio duration: 391.27 seconds
- Hardware: Apple Silicon Mac
- Package: lightning-whisper-mlx==0.0.10
- Note: Each model had a warmup run before its timed run

## Results

| Model | Quantization | Warmup Time (s) | Warmup Speed | Benchmark Time (s) | Benchmark Speed |
|-------|--------------|----------------|--------------|-------------------|----------------|
| tiny | none | 1.34 | 2.9x | 5.96 | 65.6x |
| tiny | 8bit | 7.41 | 0.5x | 6.47 | 60.5x |
| base | 8bit | 12.68 | 0.3x | 8.76 | 44.7x |
| base | none | 1.62 | 2.4x | 9.75 | 40.1x |
| small | 8bit | 32.95 | 0.1x | 10.88 | 36.0x |
| distil-medium.en | none | 2.09 | 1.9x | 11.31 | 34.6x |
| base | 4bit | 10.12 | 0.4x | 11.66 | 33.6x |
| distil-small.en | none | 1.94 | 2.0x | 12.08 | 32.4x |
| small | none | 3.89 | 1.0x | 17.34 | 22.6x |
| tiny | 4bit | 8.45 | 0.5x | 18.54 | 21.1x |
| distil-large-v2 | none | 3.99 | 1.0x | 27.40 | 14.3x |
| small | 4bit | 25.20 | 0.2x | 28.76 | 13.6x |
| distil-large-v3 | none | 3.51 | 1.1x | 29.62 | 13.2x |
| large-v3 | 4bit | 101.63 | 0.0x | 44.27 | 8.8x |
| large | 4bit | 99.71 | 0.0x | 44.53 | 8.8x |
| large | 8bit | 77.27 | 0.1x | 50.25 | 7.8x |
| large-v3 | none | 6.35 | 0.6x | 50.57 | 7.7x |
| large-v3 | 8bit | 172.90 | 0.0x | 50.82 | 7.7x |
| large | none | 306.77 | 0.0x | 53.65 | 7.3x |
| medium | 4bit | 61.63 | 0.1x | 64.76 | 6.0x |
| medium | none | 66.02 | 0.1x | 72.74 | 5.4x |
| medium | 8bit | 96.66 | 0.0x | 75.92 | 5.2x |
| large-v2 | 4bit | 113.58 | 0.0x | 178.95 | 2.2x |
| large-v2 | 8bit | 187.17 | 0.0x | 182.26 | 2.1x |
| large-v2 | none | 21.57 | 0.2x | 184.69 | 2.1x |
