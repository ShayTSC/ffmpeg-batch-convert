# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python video conversion tool that performs batch conversion of video files using FFmpeg with hardware-accelerated encoding on Apple Silicon. The tool automatically detects color profiles (DLOG-M, HLG, REC709) and applies appropriate LUT files for color grading to REC709 output.

## Development Commands

### Running the Tool
```bash
# Basic usage - convert all videos in current directory
python main.py

# Convert with specific options
python main.py -d /path/to/videos -o /path/to/output -s _converted -v

# Run with custom LUT file
python main.py -l custom.cube
```

### Dependencies
- Python 3.8+ (project uses Python 3.13)
- FFmpeg must be installed and available in PATH (`brew install ffmpeg` on macOS)
- No additional Python dependencies - uses only standard library

### Testing
Check the README.md for testing approaches as no test framework is currently configured.

## Architecture

### Core Components

**VideoConverter Class** (`main.py:35-335`)
- Main orchestrator handling the conversion pipeline
- Manages input/output directories, LUT selection, and processing statistics
- Contains all video processing logic and progress display

**VideoInfo Dataclass** (`main.py:17-26`)
- Stores metadata from ffprobe: duration, color space, primaries, transfer, dimensions, codec

**Color Profile Detection** (`main.py:112-131`)
- Auto-detects video color profiles: HLG (iPhone footage), DLOG-M (DJI footage), REC709
- Uses ffprobe metadata (color_space, color_primaries, color_transfer) for detection

### Processing Pipeline

1. **File Discovery**: Scans for `.mp4/.mov` files in input directory
2. **Video Analysis**: Uses ffprobe to extract metadata and detect color profile
3. **LUT Selection**: Auto-selects appropriate LUT file based on detected profile:
   - DLOG-M → `luts/DJI_DLogM_to_Rec709.cube`
   - HLG → `luts/iPhone_2020_to_709_33.cube`
   - REC709 → No LUT needed
4. **FFmpeg Conversion**: Hardware-accelerated HEVC encoding with VideoToolbox
5. **Progress Monitoring**: Real-time progress parsing from FFmpeg output

### FFmpeg Configuration

The tool generates FFmpeg commands with these settings:
- Hardware acceleration: VideoToolbox (macOS)
- Video codec: HEVC with hardware encoding (`hevc_videotoolbox`)
- Pixel format: `yuv420p10le` (10-bit)
- Bitrate: 20Mbps with 25Mbps max
- Color space: BT.709 output
- Audio: Copy without re-encoding

### File Structure

- `main.py` - Single file containing all functionality
- `luts/` - Color grading LUT files (.cube format)
- `conversion.log` - Detailed processing logs
- `pyproject.toml` - Project configuration and metadata

### Key Methods

- `get_video_info()` - Extracts metadata using ffprobe
- `detect_color_profile()` - Analyzes metadata to determine source color profile
- `build_ffmpeg_command()` - Constructs FFmpeg command based on color profile
- `convert_video()` - Executes FFmpeg with progress monitoring
- `process_file()` - Complete pipeline for single file conversion

### Output Naming

Default output format: `{input_stem}_REC709.mp4`
Configurable via `-s/--suffix` parameter.