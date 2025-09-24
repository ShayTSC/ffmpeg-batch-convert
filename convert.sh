#!/bin/zsh

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to display progress bar
show_progress() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r${BLUE}Overall Progress: ${NC}["
    printf "%*s" $filled | tr ' ' '█'
    printf "%*s" $empty | tr ' ' '░'
    printf "] ${GREEN}%d%%${NC} (${CYAN}%d${NC}/${CYAN}%d${NC} files)" $percentage $current $total
}

# Function to get file size in human readable format
get_file_size() {
    local file="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        stat -f%z "$file" | awk '{
            if ($1 > 1073741824) printf "%.1f GB", $1/1073741824
            else if ($1 > 1048576) printf "%.1f MB", $1/1048576
            else if ($1 > 1024) printf "%.1f KB", $1/1024
            else printf "%d B", $1
        }'
    else
        stat --printf="%s" "$file" | awk '{
            if ($1 > 1073741824) printf "%.1f GB", $1/1073741824
            else if ($1 > 1048576) printf "%.1f MB", $1/1048576
            else if ($1 > 1024) printf "%.1f KB", $1/1024
            else printf "%d B", $1
        }'
    fi
}

# Function to get video duration
get_duration() {
    local file="$1"
    ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null | awk '{
        hours = int($1/3600)
        minutes = int(($1%3600)/60)
        seconds = int($1%60)
        printf "%02d:%02d:%02d", hours, minutes, seconds
    }'
}

# Count total files to process
files=(*.(mp4|mov|MP4|MOV)(N))
total_files=${#files[@]}

if [[ $total_files -eq 0 ]]; then
    echo "${RED}Error: No MP4 or MOV files found in current directory${NC}"
    exit 1
fi

echo "${PURPLE}═══════════════════════════════════════════════════════════${NC}"
echo "${PURPLE}          Video Conversion Script - HLG Hardware Encoding${NC}"
echo "${PURPLE}═══════════════════════════════════════════════════════════${NC}"
echo
echo "${CYAN}Found ${total_files} file(s) to process${NC}"
echo

# Initialize counters
current_file=0
successful_conversions=0
failed_conversions=0
total_input_size=0
total_output_size=0
start_time=$(date +%s)

for f in "${files[@]}"; do
    [[ -f "$f" ]] || continue
    
    ((current_file++))
    out="${f:r}_HLG_hw.mp4"
    
    # Skip if output file already exists
    if [[ -f "$out" ]]; then
        echo "${YELLOW}⚠ Skipping ${f} - output file already exists${NC}"
        show_progress $current_file $total_files
        echo
        continue
    fi
    
    # Display file information
    input_size=$(get_file_size "$f")
    duration=$(get_duration "$f")
    
    echo
    echo "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${CYAN}Processing file ${current_file}/${total_files}:${NC} ${YELLOW}$f${NC}"
    echo "${BLUE}Input size:${NC} $input_size"
    echo "${BLUE}Duration:${NC} $duration"
    echo "${BLUE}Output:${NC} $out"
    echo "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Update overall progress
    show_progress $current_file $total_files
    echo
    echo
    
    # Run ffmpeg with progress output
    echo "${CYAN}Starting conversion...${NC}"
    if ffmpeg -y -hwaccel videotoolbox -i "$f" \
      -vf "lut3d='DJI_DLogM_to_Rec709.cube',zscale=primaries=bt2020:matrix=bt2020nc,format=p010le,zscale=transfer=arib-std-b67" \
      -c:v hevc_videotoolbox -pix_fmt p010le -b:v 20M -maxrate 25M -bufsize 25M \
      -tag:v hvc1 -color_primaries bt2020 -color_trc arib-std-b67 -colorspace bt2020nc \
      -movflags +faststart -c:a copy \
      -progress pipe:1 -nostats "$out" 2>&1 | while IFS= read -r line; do
        
        # Extract progress information from ffmpeg output
        if [[ "$line" =~ ^out_time_ms=([0-9]+) ]]; then
            time_ms=${line#*=}
            time_sec=$((time_ms / 1000000))
            if [[ $time_sec -gt 0 && ! -z "$duration" ]]; then
                # Calculate percentage based on duration
                total_sec=$(echo "$duration" | awk -F: '{print ($1 * 3600) + ($2 * 60) + $3}')
                if [[ $total_sec -gt 0 ]]; then
                    progress_percent=$((time_sec * 100 / total_sec))
                    if [[ $progress_percent -le 100 ]]; then
                        printf "\r${GREEN}Encoding progress: %d%% ${NC}[" $progress_percent
                        filled=$((progress_percent * 30 / 100))
                        empty=$((30 - filled))
                        printf "%*s" $filled | tr ' ' '▓'
                        printf "%*s" $empty | tr ' ' '░'
                        printf "]"
                    fi
                fi
            fi
        elif [[ "$line" =~ ^speed=([0-9.]+)x ]]; then
            speed=${line#*=}
            speed=${speed%x}
            printf " Speed: ${CYAN}${speed}x${NC}"
        fi
    done; then
        echo
        echo "${GREEN}✓ Conversion successful!${NC}"
        
        # Calculate file sizes and compression ratio
        if [[ -f "$out" ]]; then
            output_size=$(get_file_size "$out")
            input_bytes=$(stat -f%z "$f" 2>/dev/null || stat --printf="%s" "$f" 2>/dev/null)
            output_bytes=$(stat -f%z "$out" 2>/dev/null || stat --printf="%s" "$out" 2>/dev/null)
            
            if [[ -n "$input_bytes" && -n "$output_bytes" && $input_bytes -gt 0 ]]; then
                compression_ratio=$(echo "scale=1; $output_bytes * 100 / $input_bytes" | bc 2>/dev/null || echo "N/A")
                total_input_size=$((total_input_size + input_bytes))
                total_output_size=$((total_output_size + output_bytes))
                
                echo "${BLUE}Output size:${NC} $output_size (${compression_ratio}% of original)"
            else
                echo "${BLUE}Output size:${NC} $output_size"
            fi
        fi
        
        ((successful_conversions++))
    else
        echo
        echo "${RED}✗ Conversion failed!${NC}"
        ((failed_conversions++))
    fi
    
    echo
done

# Final summary
echo
echo "${PURPLE}═══════════════════════════════════════════════════════════${NC}"
echo "${PURPLE}                    CONVERSION SUMMARY${NC}"
echo "${PURPLE}═══════════════════════════════════════════════════════════${NC}"

end_time=$(date +%s)
total_time=$((end_time - start_time))
hours=$((total_time / 3600))
minutes=$(((total_time % 3600) / 60))
seconds=$((total_time % 60))

echo "${CYAN}Total files processed:${NC} $total_files"
echo "${GREEN}Successful conversions:${NC} $successful_conversions"
if [[ $failed_conversions -gt 0 ]]; then
    echo "${RED}Failed conversions:${NC} $failed_conversions"
fi
echo "${BLUE}Total processing time:${NC} $(printf "%02d:%02d:%02d" $hours $minutes $seconds)"

# Show total size comparison if we have the data
if [[ $total_input_size -gt 0 && $total_output_size -gt 0 ]]; then
    total_input_readable=$(echo $total_input_size | awk '{
        if ($1 > 1073741824) printf "%.1f GB", $1/1073741824
        else if ($1 > 1048576) printf "%.1f MB", $1/1048576
        else if ($1 > 1024) printf "%.1f KB", $1/1024
        else printf "%d B", $1
    }')
    total_output_readable=$(echo $total_output_size | awk '{
        if ($1 > 1073741824) printf "%.1f GB", $1/1073741824
        else if ($1 > 1048576) printf "%.1f MB", $1/1048576
        else if ($1 > 1024) printf "%.1f KB", $1/1024
        else printf "%d B", $1
    }')
    total_compression=$(echo "scale=1; $total_output_size * 100 / $total_input_size" | bc 2>/dev/null || echo "N/A")
    space_saved=$((total_input_size - total_output_size))
    space_saved_readable=$(echo $space_saved | awk '{
        if ($1 > 1073741824) printf "%.1f GB", $1/1073741824
        else if ($1 > 1048576) printf "%.1f MB", $1/1048576
        else if ($1 > 1024) printf "%.1f KB", $1/1024
        else printf "%d B", $1
    }')
    
    echo "${BLUE}Total input size:${NC} $total_input_readable"
    echo "${BLUE}Total output size:${NC} $total_output_readable (${total_compression}% of original)"
    echo "${GREEN}Space saved:${NC} $space_saved_readable"
fi

echo "${PURPLE}═══════════════════════════════════════════════════════════${NC}"

if [[ $successful_conversions -eq $total_files ]]; then
    echo "${GREEN}All conversions completed successfully! 🎉${NC}"
else
    echo "${YELLOW}Conversion completed with some issues.${NC}"
fi
