# FFmpeg Batch Convert

A robust Python script for batch converting video files using FFmpeg with hardware-accelerated encoding and automatic color profile detection. Converts DLOG-M, HLG, and other formats to REC709 with appropriate color grading.

## Features

- **Batch Processing**: Automatically processes all MP4/MOV files in a directory
- **Hardware Acceleration**: Uses VideoToolbox on macOS for efficient encoding
- **Automatic Color Profile Detection**: Detects DLOG-M, HLG, and REC709 color profiles
- **Smart LUT Application**: Automatically applies appropriate LUT files for color grading
- **Progress Tracking**: Real-time progress bars for individual files and overall progress
- **Comprehensive Logging**: Detailed logs with conversion statistics
- **Error Handling**: Robust error handling with detailed error messages
- **Flexible Configuration**: Command-line options for customization
- **Skip Existing**: Automatically skips files that have already been converted
- **Size Comparison**: Shows input/output file sizes and compression ratios

## Prerequisites

- **Python 3.8+**: Required for running the script
- **FFmpeg**: Must be installed and available in your PATH
  - On macOS: `brew install ffmpeg`
  - On Ubuntu/Debian: `sudo apt install ffmpeg`
  - On Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Installation

### Option 1: Direct Use
1. Clone or download this repository
2. Make sure FFmpeg is installed and accessible from command line
3. The script is ready to use - no additional Python dependencies required

### Option 2: Install as Package
```bash
# Install using uv (recommended)
uv sync

# Or install using pip
pip install -e .

# Then run from anywhere
ffmpeg-batch-convert
```

## Usage

### Basic Usage

Convert all video files in the current directory:
```bash
python main.py
```

### Advanced Usage

```bash
# Convert files in a specific directory
python main.py -d /path/to/videos

# Use a custom output suffix
python main.py -s _converted

# Use a custom LUT file
python main.py -l my_custom_lut.cube

# Enable verbose logging
python main.py -v

# Combine options
python main.py -d /path/to/videos -s _hlg_converted -v
```

### Command Line Options

- `-d, --directory`: Input directory containing video files (default: current directory)
- `-o, --output`: Output directory (default: same as input directory)
- `-s, --suffix`: Output file suffix (default: `_REC709`)
- `-l, --lut`: Custom LUT file for color grading (auto-selects by default)
- `-v, --verbose`: Enable verbose logging
- `-h, --help`: Show help message

## Output

The script provides:

1. **Real-time Progress**: Shows encoding progress for each file
2. **File Information**: Displays input size, duration, and output filename
3. **Conversion Summary**: Final statistics including:
   - Total files processed
   - Success/failure counts
   - Total processing time
   - File size comparisons
   - Space saved

## Technical Details

### FFmpeg Settings

The script uses the following FFmpeg configuration:

- **Hardware Acceleration**: VideoToolbox (macOS)
- **Codec**: HEVC (H.265) with hardware encoding
- **Pixel Format**: YUV420P10LE (10-bit)
- **Bitrate**: 20Mbps with 25Mbps max rate
- **Output Color Space**: BT.709 (REC709)
- **Audio**: Copy without re-encoding

### Color Profile Detection & LUT Application

- **DLOG-M** (DJI footage): Applies `luts/DJI_DLogM_to_Rec709.cube`
- **HLG** (iPhone footage): Applies `luts/iPhone_2020_to_709_33.cube`
- **REC709**: No LUT needed, direct encoding
- **Unknown**: Defaults to DLOG-M LUT

### File Processing

- Supports: `.mp4`, `.mov`, `.MP4`, `.MOV` files
- Output format: MP4 with HEVC encoding
- Automatically skips existing output files
- Creates detailed logs in `conversion.log`

## Error Handling

The script includes comprehensive error handling:

- Dependency checking (FFmpeg/ffprobe availability)
- File access permissions
- FFmpeg process errors
- Timeout handling for long operations
- Graceful handling of user interruption (Ctrl+C)

## Logging

- Console output with colored progress indicators
- Detailed log file (`conversion.log`) with timestamps
- Error tracking and reporting
- Processing statistics and summaries

## Performance

- Hardware-accelerated encoding for optimal performance
- Real-time progress monitoring
- Efficient memory usage
- Parallel-ready architecture (can be extended for concurrent processing)

## Architecture

The tool is built around a single `VideoConverter` class that handles the entire conversion pipeline:

1. **File Discovery**: Scans for video files in the input directory
2. **Metadata Analysis**: Uses ffprobe to extract color profile information
3. **Color Profile Detection**: Automatically detects DLOG-M, HLG, or REC709 profiles
4. **LUT Selection**: Chooses appropriate LUT file based on detected profile
5. **Hardware-Accelerated Conversion**: Executes FFmpeg with VideoToolbox acceleration
6. **Progress Monitoring**: Real-time progress parsing and display

### Key Components

- **VideoInfo**: Dataclass storing video metadata (duration, color space, dimensions)
- **Color Profile Detection**: Analyzes ffprobe metadata to determine source format
- **FFmpeg Command Builder**: Constructs appropriate FFmpeg commands with LUT filters
- **Progress Display**: Real-time encoding progress with colored terminal output

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### FFmpeg Not Found
```
Error: ffmpeg not found in PATH
```
Solution: Install FFmpeg and ensure it's in your system PATH.

### Permission Denied
```
PermissionError: [Errno 13] Permission denied
```
Solution: Check file permissions and ensure you have write access to the output directory.

### Hardware Acceleration Issues
If hardware acceleration fails, the script will fall back to software encoding. Check your system's VideoToolbox support.

### Large File Processing
For very large files, consider:
- Ensuring sufficient disk space
- Monitoring system resources
- Using the verbose flag to track progress