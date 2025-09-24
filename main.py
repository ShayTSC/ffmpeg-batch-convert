#!/usr/bin/env python3
"""Video Conversion Script - HLG Hardware Encoding for Apple Silicon"""

import sys
import time
import re
import argparse
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import shutil

try:
    import ffmpeg
except ImportError:
    print("Error: ffmpeg-python not installed. Run: pip install ffmpeg-python")
    sys.exit(1)


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
                 output_suffix: str = "_HLG_hw", lut_file: str = "DJI_DLogM_to_Rec709.cube"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else None
        self.output_suffix = output_suffix
        self.lut_file = lut_file

        self.stats = {
            'successful': 0, 'failed': 0,
            'input_size': 0, 'output_size': 0, 'start_time': 0
        }

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler('conversion.log'), logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    def check_dependencies(self) -> bool:
        if not shutil.which('ffmpeg'):
            print(f"{Colors.RED}Error: ffmpeg not found. Install from https://ffmpeg.org{Colors.NC}")
            return False
        return True

    def get_video_files(self) -> List[Path]:
        return sorted(f for ext in self.EXTENSIONS for f in self.input_dir.glob(f"*{ext}"))

    @staticmethod
    def format_size(size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0 or unit == 'TB':
                return f"{size:.1f} {unit}"
            size /= 1024.0

    @staticmethod
    def format_duration(seconds: float) -> str:
        h, m = divmod(int(seconds), 3600)
        m, s = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_video_info(self, file_path: Path) -> VideoInfo:
        try:
            probe = ffmpeg.probe(str(file_path))
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)

            if video_stream:
                return VideoInfo(
                    duration=float(probe['format'].get('duration', 0)),
                    color_space=video_stream.get('color_space', 'unknown'),
                    color_primaries=video_stream.get('color_primaries', 'unknown'),
                    color_transfer=video_stream.get('color_trc', 'unknown'),
                    width=video_stream.get('width', 0),
                    height=video_stream.get('height', 0),
                    codec_name=video_stream.get('codec_name', 'unknown')
                )
        except ffmpeg.Error as e:
            self.logger.warning(f"Could not probe {file_path}: {e}")

        return VideoInfo()

    @staticmethod
    def detect_color_profile(video_info: VideoInfo) -> str:
        cs, cp, ct = (video_info.color_space.lower(),
                     video_info.color_primaries.lower(),
                     video_info.color_transfer.lower())

        if 'dlogm' in cs or 'dlogm' in ct or ('bt709' in cp and 'unknown' in ct):
            return 'dlogm'
        if 'bt709' in cs or 'bt709' in cp or 'bt709' in ct or 'srgb' in ct:
            return 'rec709'
        return 'unknown'

    def build_ffmpeg_stream(self, input_path: Path, output_path: Path, color_profile: str):
        profile_filters = {
            'dlogm': f"lut3d='{self.lut_file}',zscale=primaries=bt2020:matrix=bt2020nc,format=p010le,zscale=transfer=arib-std-b67",
            'rec709': "zscale=primaries=bt2020:matrix=bt2020nc,format=p010le,zscale=transfer=arib-std-b67",
        }

        video_filter = profile_filters.get(color_profile, profile_filters['dlogm'])

        profile_msgs = {
            'dlogm': f"{Colors.BLUE}DLogM → REC709 → REC2020{Colors.NC}",
            'rec709': f"{Colors.BLUE}REC709 → REC2020{Colors.NC}",
            'unknown': f"{Colors.YELLOW}Unknown → Assuming DLogM{Colors.NC}"
        }
        print(f"Color Profile: {profile_msgs.get(color_profile, profile_msgs['unknown'])}")

        stream = (
            ffmpeg
            .input(str(input_path), hwaccel='videotoolbox')
            .filter('scale', video_filter)
            .output(
                str(output_path),
                vcodec='hevc_videotoolbox',
                pix_fmt='p010le',
                video_bitrate='20M',
                maxrate='25M',
                bufsize='25M',
                acodec='copy',
                **{
                    'tag:v': 'hvc1',
                    'color_primaries': 'bt2020',
                    'color_trc': 'arib-std-b67',
                    'colorspace': 'bt2020nc',
                    'movflags': '+faststart'
                }
            )
            .global_args('-progress', 'pipe:1', '-nostats')
            .overwrite_output()
        )

        return stream

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
            bar = '▓' * (pct * width // 100) + '░' * (width - pct * width // 100)
            speed_txt = f" {Colors.CYAN}{speed:.1f}x{Colors.NC}" if speed else ""
            print(f"\r{Colors.GREEN}Encoding: {pct}%{Colors.NC} [{bar}]{speed_txt}", end='', flush=True)

    def convert_video(self, input_path: Path, output_path: Path, color_profile: str) -> bool:
        try:
            stream = self.build_ffmpeg_stream(input_path, output_path, color_profile)
            video_info = self.get_video_info(input_path)

            print(f"{Colors.CYAN}Converting...{Colors.NC}")

            process = stream.run_async(pipe_stdout=True, pipe_stderr=True)
            last_update = time.time()

            for line in process.stdout:
                line_str = line.decode('utf-8', errors='ignore')
                if match := re.search(r'out_time_ms=(\d+)', line_str):
                    time_ms = int(match.group(1))
                    speed_match = re.search(r'speed=([0-9.]+)x', line_str)
                    speed = float(speed_match.group(1)) if speed_match else None

                    if time.time() - last_update >= 0.5:
                        self.show_encoding_progress(time_ms, video_info.duration, speed)
                        last_update = time.time()

            process.wait()
            print()
            return process.returncode == 0

        except ffmpeg.Error as e:
            self.logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Conversion error: {e}")
            return False

    def process_file(self, input_path: Path, idx: int, total: int) -> bool:
        output_path = (self.output_dir or input_path.parent) / f"{input_path.stem}{self.output_suffix}.mp4"

        if output_path.exists():
            print(f"{Colors.YELLOW}⚠ Skipping {input_path.name} - exists{Colors.NC}")
            return True

        try:
            input_size = input_path.stat().st_size
            video_info = self.get_video_info(input_path)
            color_profile = self.detect_color_profile(video_info)

            print(f"\n{Colors.PURPLE}{'━' * 61}{Colors.NC}")
            print(f"{Colors.CYAN}[{idx}/{total}]{Colors.NC} {Colors.YELLOW}{input_path.name}{Colors.NC}")
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
                ratio = (output_size * 100.0) / input_size if input_size > 0 else 0

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
            ratio = (self.stats['output_size'] * 100.0) / self.stats['input_size']
            print(f"{Colors.BLUE}Input:{Colors.NC} {self.format_size(self.stats['input_size'])} → "
                  f"{Colors.BLUE}Output:{Colors.NC} {self.format_size(self.stats['output_size'])} "
                  f"({ratio:.1f}%) | "
                  f"{Colors.GREEN}Saved:{Colors.NC} {self.format_size(saved)}")

        print(f"{Colors.PURPLE}{'═' * 61}{Colors.NC}")

        if self.stats['successful'] == total:
            print(f"{Colors.GREEN}All conversions successful! 🎉{Colors.NC}")

    def run(self) -> int:
        print(f"{Colors.PURPLE}{'═' * 61}{Colors.NC}")
        print(f"{Colors.PURPLE}{'HLG Hardware Encoding (Apple Silicon)':^61}{Colors.NC}")
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
    parser.add_argument('-s', '--suffix', default='_HLG_hw',
                       help='Output suffix (default: _HLG_hw)')
    parser.add_argument('-l', '--lut', default='DJI_DLogM_to_Rec709.cube',
                       help='LUT file (default: DJI_DLogM_to_Rec709.cube)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        converter = VideoConverter(args.directory, args.output, args.suffix, args.lut)
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