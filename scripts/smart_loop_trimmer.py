#!/usr/bin/env python3
"""
smart_loop_trimmer.py
Detects and removes both start settling and end return-to-start frames 
from AI-generated loops to create smoother concatenation.
"""

import json, os, subprocess, sys
from pathlib import Path
import cv2
import numpy as np

FFMPEG = os.getenv("FFMPEG", "ffmpeg")

def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)

def extract_frame(video_path, timestamp, output_path):
    """Extract a single frame at specified timestamp"""
    cmd = [
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(timestamp), "-i", str(video_path),
        "-frames:v", "1", str(output_path)
    ]
    subprocess.run(cmd, check=True)

def calculate_frame_similarity(frame1_path, frame2_path):
    """Calculate similarity between two frames using histogram comparison"""
    try:
        img1 = cv2.imread(str(frame1_path))
        img2 = cv2.imread(str(frame2_path))
        
        if img1 is None or img2 is None:
            return 0.0
        
        # Convert to HSV for better color comparison
        hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
        hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
        
        # Calculate histograms
        hist1 = cv2.calcHist([hsv1], [0, 1, 2], None, [50, 60, 60], [0, 180, 0, 256, 0, 256])
        hist2 = cv2.calcHist([hsv2], [0, 1, 2], None, [50, 60, 60], [0, 180, 0, 256, 0, 256])
        
        # Compare histograms
        similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return max(0.0, similarity)
    except Exception:
        return 0.0

def find_clean_motion_segment(video_path, duration):
    """
    Find the clean motion segment by trimming both start and end
    Removes initial settling and final return-to-start portions
    """
    temp_dir = Path("temp_frames")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Extract reference frame from very beginning
        first_frame = temp_dir / "first.jpg"
        extract_frame(video_path, 0.1, first_frame)
        
        # Find where actual motion starts (trim beginning)
        motion_start = duration * 0.1  # Default start
        for check_time in [0.2, 0.4, 0.6, 0.8, 1.0]:
            if check_time >= duration * 0.8:
                break
                
            test_frame = temp_dir / f"start_{check_time:.1f}.jpg"
            try:
                extract_frame(video_path, check_time, test_frame)
                similarity = calculate_frame_similarity(first_frame, test_frame)
                
                # When similarity drops below threshold, real motion has started
                if similarity < 0.85:  # Motion has clearly begun
                    motion_start = check_time
                    break
                    
                test_frame.unlink()
            except Exception:
                pass
        
        # Find where return journey starts (trim end)
        motion_end = duration * 0.7  # Default end
        max_difference = 0.0
        
        # Sample through the middle portion to find peak motion
        for check_time in np.arange(motion_start + 0.5, duration * 0.85, 0.15):
            test_frame = temp_dir / f"end_{check_time:.1f}.jpg"
            try:
                extract_frame(video_path, check_time, test_frame)
                similarity = calculate_frame_similarity(first_frame, test_frame)
                difference = 1.0 - similarity
                
                if difference > max_difference:
                    max_difference = difference
                    motion_end = check_time + 0.2  # Add small buffer after peak
                
                test_frame.unlink()
            except Exception:
                pass
        
        # Ensure reasonable bounds
        motion_start = max(motion_start, duration * 0.05)  # Don't trim more than 5% from start
        motion_end = min(motion_end, duration * 0.85)      # Don't trim more than 15% from end
        motion_end = max(motion_end, motion_start + 1.0)   # Ensure at least 1 second remains
        
        clean_duration = motion_end - motion_start
        
        # Clean up temp files
        for f in temp_dir.glob("*.jpg"):
            f.unlink()
        temp_dir.rmdir()
        
        return motion_start, clean_duration, max_difference
        
    except Exception as e:
        print(f"Error finding clean motion segment in {video_path}: {e}")
        return duration * 0.2, duration * 0.6, 0.0

def get_video_duration(video_path):
    """Get video duration using ffprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "default=nokey=1:noprint_wrappers=1", str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception:
        return 5.0  # Default duration

def process_smart_manifest_with_loop_detection(manifest_path, out_dir):
    """Process smart manifest and add loop detection trimming"""
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest_data = json.load(f)
    
    items = manifest_data.get("items", [])
    if not items:
        die("No items in manifest")
    
    print("Detecting AI loop points for smoother concatenation...")
    
    processed_items = []
    total_saved_time = 0.0
    
    for i, item in enumerate(items):
        video_path = item.get("path")
        if not video_path or not os.path.exists(video_path):
            continue
        
        # Get original duration
        original_duration = get_video_duration(video_path)
        
        # Find clean motion segment (trim both start and end)
        start_trim, clean_duration, motion_strength = find_clean_motion_segment(video_path, original_duration)
        
        # Update item with start trim and clean duration
        new_item = item.copy()
        new_item["original_duration"] = original_duration
        new_item["start_trim"] = start_trim
        new_item["clean_duration"] = clean_duration
        new_item["motion_strength"] = motion_strength
        new_item["t1"] = new_item["t0"] + clean_duration
        
        total_trimmed = original_duration - clean_duration
        total_saved_time += total_trimmed
        
        status = "CLEAN MOTION" if motion_strength > 0.3 else "BASIC TRIM"
        print(f"  {Path(video_path).name}: {original_duration:.1f}s → {clean_duration:.1f}s "
              f"(start: +{start_trim:.1f}s, total trim: {total_trimmed:.1f}s) [{status}]")
        
        processed_items.append(new_item)
    
    # Update manifest
    manifest_data["items"] = processed_items
    manifest_data["loop_detection"] = {
        "total_clips": len(processed_items),
        "total_time_saved": total_saved_time,
        "trimming_method": "start_and_end"
    }
    
    # Save updated manifest
    loop_manifest_path = out_dir / "smart_manifest_loop_trimmed.json"
    with open(loop_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2)
    
    print(f"\nLoop detection complete:")
    print(f"  Total time saved: {total_saved_time:.1f}s")
    print(f"  Average per clip: {total_saved_time/len(processed_items):.1f}s")
    print(f"  Updated manifest: {loop_manifest_path}")
    
    return loop_manifest_path

def create_trimmed_video(manifest_path, out_dir):
    """Create final video using loop-trimmed clips"""
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest_data = json.load(f)
    
    items = manifest_data.get("items", [])
    if not items:
        die("No items in manifest")
    
    print(f"\nCreating video with {len(items)} loop-trimmed clips...")
    
    # Build FFmpeg inputs and filters
    inputs = []
    filter_parts = []
    
    for i, item in enumerate(items):
        video_path = item.get("path")
        start_time = item.get("start_trim", 0.0)
        trimmed_duration = item.get("clean_duration", 5.0)
        
        inputs.extend(["-i", str(video_path)])
        
        # Trim both start and duration
        filter_parts.append(
            f"[{i}:v]trim=start={start_time}:duration={trimmed_duration},setpts=PTS-STARTPTS[v{i}]"
        )
    
    # Concatenate all trimmed clips
    v_inputs = "".join([f"[v{i}]" for i in range(len(items))])
    filter_parts.append(f"{v_inputs}concat=n={len(items)}:v=1:a=0[v]")
    
    filter_complex = ";".join(filter_parts)
    
    # Output file
    output_mp4 = out_dir / "combined_smooth_loops.mp4"
    
    # Build FFmpeg command
    cmd = [
        FFMPEG, "-y"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        str(output_mp4)
    ]
    
    print(f"Generating: {output_mp4.name}")
    
    # Execute
    proc = subprocess.run(cmd, text=True, capture_output=True)
    
    if proc.returncode != 0:
        print("FFmpeg error:")
        print(proc.stderr[-1000:])
        die("FFmpeg failed", proc.returncode)
    
    print(f"\nSuccess! Created smooth-flow video: {output_mp4}")
    
    # Summary
    total_duration = sum(item.get("clean_duration", 5.0) for item in items)
    total_saved = manifest_data.get("loop_detection", {}).get("total_time_saved", 0)
    
    print(f"\nSummary:")
    print(f"  Final duration: {total_duration:.1f}s")
    print(f"  Time saved by trimming loops: {total_saved:.1f}s")
    print(f"  Clips processed: {len(items)}")
    print(f"  Result: Smoother flow without AI loop resets")

def main():
    if len(sys.argv) < 2:
        die(f"Usage: {sys.argv[0]} <OUT_DIR>")
    
    out_dir = Path(sys.argv[1]).resolve()
    
    # Look for smart manifest
    smart_manifest = out_dir / "smart_manifest.json"
    if not smart_manifest.exists():
        die(f"Smart manifest not found: {smart_manifest}")
    
    print("AI Loop Trimmer - Removing return-to-start frames for smoother flow")
    print("=" * 60)
    
    # Process manifest with loop detection
    loop_manifest = process_smart_manifest_with_loop_detection(smart_manifest, out_dir)
    
    # Create final video
    create_trimmed_video(loop_manifest, out_dir)

if __name__ == "__main__":
    main()