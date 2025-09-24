# FFmpeg Batch Convert

A robust Python script for batch converting video files using FFmpeg with HLG (Hybrid Log-Gamma) hardware encoding.

## Features

- **Batch Processing**: Automatically processes all MP4/MOV files in a directory
- **Hardware Acceleration**: Uses VideoToolbox on macOS for efficient encoding
- **HLG Encoding**: Converts videos to HLG format with proper color space handling
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

1. Clone or download this repository
2. Make sure FFmpeg is installed and accessible from command line
3. The script is ready to use - no additional Python dependencies required

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
- `-s, --suffix`: Output file suffix (default: `_HLG_hw`)
- `-l, --lut`: LUT file for color grading (default: `DJI_DLogM_to_Rec709.cube`)
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
- **Pixel Format**: P010LE (10-bit)
- **Bitrate**: 20Mbps with 25Mbps max rate
- **Color Space**: BT.2020
- **Transfer Function**: ARIB-STD-B67 (HLG)
- **Audio**: Copy without re-encoding

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

## Migration from Shell Script

This Python version provides several improvements over the original shell script:

- **Better Error Handling**: More robust error detection and recovery
- **Cross-Platform**: Works on macOS, Linux, and Windows
- **Extensible**: Easy to add new features and options
- **Maintainable**: Clean, documented code structure
- **Configurable**: Command-line options for flexibility
- **Logging**: Comprehensive logging system

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