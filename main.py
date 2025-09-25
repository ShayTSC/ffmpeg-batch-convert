#!/usr/bin/env python3
"""Video Conversion Script - HLG Hardware Encoding for Apple Silicon"""

import sys
import time
import re
import argparse
import logging
import subprocess
import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import shutil


@dataclass
class VideoInfo:
    duration: float = 0
    color_space: str = 'unknown'
    color_primaries: str = 'unknown'
    color_transfer: str = 'unknown'
    width: int = 0
    height: int = 0
    codec_name: str = 'unknown'


class Colors:
    RED, GREEN, YELLOW, BLUE, PURPLE, CYAN, NC = (
        '\033[0;31m', '\033[0;32m', '\033[1;33m',
        '\033[0;34m', '\033[0;35m', '\033[0;36m', '\033[0m'
    )


class VideoConverter:
    EXTENSIONS = {'.mp4', '.mov', '.MP4', '.MOV'}

    def __init__(self, input_dir: str = ".", output_dir: Optional[str] = None,
                 output_suffix: str = "_REC709", lut_file: Optional[str] = None):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else None
        self.output_suffix = output_suffix
        self.custom_lut_file = lut_file

        # LUT file paths
        self.dlogm_lut = "luts/DJI_DLogM_to_Rec709.cube"
        self.hlg_lut = "luts/iPhone_2020_to_709_33.cube"

        self.stats = {
            'successful': 0, 'failed': 0,
            'input_size': 0, 'output_size': 0, 'start_time': 0.0
        }

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(
                'conversion.log'), logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    def check_dependencies(self) -> bool:
        if not shutil.which('ffmpeg'):
            print(
                f"{Colors.RED}Error: ffmpeg not found. Install from https://ffmpeg.org{Colors.NC}")
            return False
        return True

    def get_video_files(self) -> List[Path]:
        return sorted(f for ext in self.EXTENSIONS for f in self.input_dir.glob(f"*{ext}"))

    @staticmethod
    def format_size(size: int) -> str:
        size_float = float(size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_float < 1024.0 or unit == 'TB':
                return f"{size_float:.1f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.1f} TB"

    @staticmethod
    def format_duration(seconds: float) -> str:
        h, m = divmod(int(seconds), 3600)
        m, s = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_video_info(self, file_path: Path) -> VideoInfo:
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe = json.loads(result.stdout)
            video_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'video'), None)

            if video_stream:
                return VideoInfo(
                    duration=float(probe['format'].get('duration', 0)),
                    color_space=video_stream.get('color_space', 'unknown'),
                    color_primaries=video_stream.get(
                        'color_primaries', 'unknown'),
                    color_transfer=video_stream.get('color_trc', 'unknown'),
                    width=video_stream.get('width', 0),
                    height=video_stream.get('height', 0),
                    codec_name=video_stream.get('codec_name', 'unknown')
                )
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            self.logger.warning(f"Could not probe {file_path}: {e}")

        return VideoInfo()

    @staticmethod
    def detect_color_profile(video_info: VideoInfo) -> str:
        cs, cp, ct = (video_info.color_space.lower(),
                      video_info.color_primaries.lower(),
                      video_info.color_transfer.lower())

        # Detect HLG (iPhone footage)
        if ('arib-std-b67' in ct or 'hlg' in ct or
            ('bt2020' in cp and 'arib-std-b67' in ct)):
            return 'hlg'

        # Detect DLOG-M (DJI footage) - pseudo RAW format
        if ('dlogm' in cs or 'dlogm' in ct or 'd-log' in cs or 'd-log' in ct or
            ('bt709' in cp and 'unknown' in ct and video_info.codec_name.lower() in ['h264', 'h265', 'hevc'])):
            return 'dlogm'

        # Standard REC709
        if 'bt709' in cs or 'bt709' in cp or 'bt709' in ct or 'srgb' in ct:
            return 'rec709'

        return 'unknown'

    def build_ffmpeg_command(self, input_path: Path, output_path: Path, color_profile: str) -> List[str]:
        # Use custom LUT if specified, otherwise auto-select based on color profile
        if self.custom_lut_file:
            lut_file = self.custom_lut_file
            video_filter = f"lut3d='{lut_file}'"
            profile_msg = f"{Colors.BLUE}Custom LUT: {lut_file}{Colors.NC}"
        else:
            # Auto-select LUT and create filter chain for REC709 output
            if color_profile == 'dlogm':
                lut_file = self.dlogm_lut
                video_filter = f"lut3d='{lut_file}'"
                profile_msg = f"{Colors.BLUE}DLOG-M → REC709 (via LUT){Colors.NC}"
            elif color_profile == 'hlg':
                lut_file = self.hlg_lut
                video_filter = f"lut3d='{lut_file}'"
                profile_msg = f"{Colors.BLUE}HLG REC2020 → REC709 (via LUT){Colors.NC}"
            elif color_profile == 'rec709':
                video_filter = "scale"
                profile_msg = f"{Colors.GREEN}Already REC709 - No conversion needed{Colors.NC}"
            else:
                # Unknown - default to DLOG-M LUT
                lut_file = self.dlogm_lut
                video_filter = f"lut3d='{lut_file}'"
                profile_msg = f"{Colors.YELLOW}Unknown → Assuming DLOG-M{Colors.NC}"

        print(f"Color Profile: {profile_msg}")

        cmd = [
            'ffmpeg',
            '-hwaccel', 'videotoolbox',
            '-i', str(input_path),
            '-vf', video_filter,
            '-c:v', 'hevc_videotoolbox',
            '-pix_fmt', 'yuv420p10le',
            '-b:v', '20M',
            '-maxrate', '25M',
            '-bufsize', '25M',
            '-c:a', 'copy',
            '-tag:v', 'hvc1',
            '-color_primaries', 'bt709',
            '-color_trc', 'bt709',
            '-colorspace', 'bt709',
            '-movflags', '+faststart',
            '-progress', 'pipe:1',
            '-nostats',
            '-y',
            str(output_path)
        ]

        return cmd

    def show_progress(self, current: int, total: int) -> None:
        width, pct = 50, (current * 100) // total
        filled = (current * width) // total
        bar = '█' * filled + '░' * (width - filled)
        print(f"\r{Colors.BLUE}Overall:{Colors.NC} [{bar}] {Colors.GREEN}{pct}%{Colors.NC} "
              f"({Colors.CYAN}{current}/{total}{Colors.NC})", end='', flush=True)

    def show_encoding_progress(self, time_ms: int, duration: float, speed: Optional[float] = None):
        if duration > 0:
            time_sec = time_ms // 1000000
            pct = min(100, (time_sec * 100) // int(duration))
            width = 30
            bar = '▓' * (pct * width // 100) + '░' * \
                (width - pct * width // 100)
            speed_txt = f" {Colors.CYAN}{speed:.1f}x{Colors.NC}" if speed else ""
            print(
                f"\r{Colors.GREEN}Encoding: {pct}%{Colors.NC} [{bar}]{speed_txt}", end='', flush=True)

    def convert_video(self, input_path: Path, output_path: Path, color_profile: str) -> bool:
        try:
            cmd = self.build_ffmpeg_command(
                input_path, output_path, color_profile)
            video_info = self.get_video_info(input_path)

            print(f"{Colors.CYAN}Converting...{Colors.NC}")

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            last_update = time.time()

            if process.stdout:
                for line in process.stdout:
                    line_str = line.decode('utf-8', errors='ignore')
                    if match := re.search(r'out_time_ms=(\d+)', line_str):
                        time_ms = int(match.group(1))
                        speed_match = re.search(r'speed=([0-9.]+)x', line_str)
                        speed = float(speed_match.group(
                            1)) if speed_match else None

                        if time.time() - last_update >= 0.5:
                            self.show_encoding_progress(
                                time_ms, video_info.duration, speed)
                            last_update = time.time()

            process.wait()
            print()
            return process.returncode == 0

        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Conversion error: {e}")
            return False

    def process_file(self, input_path: Path, idx: int, total: int) -> bool:
        output_path = (self.output_dir or input_path.parent) / \
            f"{input_path.stem}{self.output_suffix}.mp4"

        try:
            input_size = input_path.stat().st_size
            video_info = self.get_video_info(input_path)
            color_profile = self.detect_color_profile(video_info)

            print(f"\n{Colors.PURPLE}{'━' * 61}{Colors.NC}")
            print(
                f"{Colors.CYAN}[{idx}/{total}]{Colors.NC} {Colors.YELLOW}{input_path.name}{Colors.NC}")
            print(f"{Colors.BLUE}Size:{Colors.NC} {self.format_size(input_size)} | "
                  f"{Colors.BLUE}Duration:{Colors.NC} {self.format_duration(video_info.duration)} | "
                  f"{Colors.BLUE}Res:{Colors.NC} {video_info.width}x{video_info.height}")
            print(f"{Colors.BLUE}Color:{Colors.NC} {video_info.color_space} / "
                  f"{video_info.color_primaries} / {video_info.color_transfer}")
            print(f"{Colors.PURPLE}{'━' * 61}{Colors.NC}")

            self.show_progress(idx, total)
            print("\n")

            if self.convert_video(input_path, output_path, color_profile):
                output_size = output_path.stat().st_size
                ratio = (output_size * 100.0) / \
                    input_size if input_size > 0 else 0

                print(f"{Colors.GREEN}✓ Success!{Colors.NC} "
                      f"{Colors.BLUE}Output:{Colors.NC} {self.format_size(output_size)} ({ratio:.1f}%)")

                self.stats['successful'] += 1
                self.stats['input_size'] += input_size
                self.stats['output_size'] += output_size
                return True
            else:
                print(f"{Colors.RED}✗ Failed{Colors.NC}")
                self.stats['failed'] += 1
                return False

        except Exception as e:
            print(f"{Colors.RED}✗ Error: {e}{Colors.NC}")
            self.logger.error(f"Processing error for {input_path}: {e}")
            self.stats['failed'] += 1
            return False

    def print_summary(self, total: int):
        elapsed = self.format_duration(time.time() - self.stats['start_time'])

        print(f"\n{Colors.PURPLE}{'═' * 61}{Colors.NC}")
        print(f"{Colors.PURPLE}{'SUMMARY':^61}{Colors.NC}")
        print(f"{Colors.PURPLE}{'═' * 61}{Colors.NC}")
        print(f"{Colors.CYAN}Total:{Colors.NC} {total} | "
              f"{Colors.GREEN}Success:{Colors.NC} {self.stats['successful']} | "
              f"{Colors.RED}Failed:{Colors.NC} {self.stats['failed']} | "
              f"{Colors.BLUE}Time:{Colors.NC} {elapsed}")

        if self.stats['input_size'] > 0:
            saved = self.stats['input_size'] - self.stats['output_size']
            ratio = (self.stats['output_size'] * 100.0) / \
                self.stats['input_size']
            print(f"{Colors.BLUE}Input:{Colors.NC} {self.format_size(self.stats['input_size'])} → "
                  f"{Colors.BLUE}Output:{Colors.NC} {self.format_size(self.stats['output_size'])} "
                  f"({ratio:.1f}%) | "
                  f"{Colors.GREEN}Saved:{Colors.NC} {self.format_size(saved)}")

        print(f"{Colors.PURPLE}{'═' * 61}{Colors.NC}")

        if self.stats['successful'] == total:
            print(f"{Colors.GREEN}All conversions successful! 🎉{Colors.NC}")

    def run(self) -> int:
        print(f"{Colors.PURPLE}{'═' * 61}{Colors.NC}")
        print(
            f"{Colors.PURPLE}{'Auto REC709 Color Grading (Apple Silicon)':^61}{Colors.NC}")
        print(f"{Colors.PURPLE}{'═' * 61}{Colors.NC}")

        if not self.check_dependencies():
            return 1

        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            print(f"{Colors.GREEN}Output: {self.output_dir}{Colors.NC}")

        files = self.get_video_files()
        if not files:
            print(f"{Colors.RED}No video files found in {self.input_dir}{Colors.NC}")
            return 1

        print(f"{Colors.CYAN}Found {len(files)} file(s){Colors.NC}\n")
        self.stats['start_time'] = time.time()

        for i, file_path in enumerate(files, 1):
            self.process_file(file_path, i, len(files))

        self.print_summary(len(files))
        return 0 if self.stats['failed'] == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description='Convert videos with HLG hardware encoding (Apple Silicon optimized)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s                      # Current directory
  %(prog)s -d /videos           # Specific input directory
  %(prog)s -o /output           # Specific output directory
  %(prog)s -s _converted        # Custom suffix
  %(prog)s -l custom.cube       # Custom LUT file

Installation:
  pip install ffmpeg-python"""
    )

    parser.add_argument('-d', '--directory', default='.',
                        help='Input directory (default: current)')
    parser.add_argument('-o', '--output',
                        help='Output directory (default: same as input)')
    parser.add_argument('-s', '--suffix', default='_REC709',
                        help='Output suffix (default: _REC709)')
    parser.add_argument('-l', '--lut',
                        help='Custom LUT file (optional - auto-selects by default)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        converter = VideoConverter(
            args.directory, args.output, args.suffix, args.lut)
        return converter.run()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted{Colors.NC}")
        return 130
    except Exception as e:
        print(f"{Colors.RED}Fatal: {e}{Colors.NC}")
        logging.error(f"Fatal: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
