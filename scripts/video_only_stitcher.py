#!/usr/bin/env python3
"""
video_only_stitcher.py
AI-optimized sequencing with video only, no audio processing
"""

import json, os, subprocess, sys
from pathlib import Path

FFMPEG = os.getenv("FFMPEG", "ffmpeg")

def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)

def main():
    if len(sys.argv) < 2:
        die(f"Usage: {sys.argv[0]} <OUT_DIR>")
    
    out_dir = Path(sys.argv[1]).resolve()
    
    # Try smart manifest first
    smart_manifest = out_dir / "smart_manifest.json"
    regular_manifest = out_dir / "manifest.json"
    
    if smart_manifest.exists():
        manifest_path = smart_manifest
        print("Using AI-optimized sequence (video only)...")
    elif regular_manifest.exists():
        manifest_path = regular_manifest
        print("Using regular manifest (video only)...")
    else:
        die(f"No manifest found in {out_dir}")
    
    # Load manifest
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    except Exception as e:
        die(f"Could not read manifest: {e}")
    
    # Parse manifest
    if isinstance(manifest_data, list):
        items = manifest_data
        transitions = []
    else:
        items = manifest_data.get("items", [])
        transitions = manifest_data.get("transitions", [])
    
    if not items:
        die("No items found in manifest")
    
    # Validate files
    valid_items = []
    for item in items:
        path = item.get("path")
        if path and os.path.exists(path):
            valid_items.append(item)
    
    if not valid_items:
        die("No valid files found")
    
    print(f"Processing {len(valid_items)} clips (video only, clean cuts)...")
    
    # Build simple video-only filter
    inputs = []
    filter_parts = []
    
    for i, item in enumerate(valid_items):
        path = item.get("path")
        inputs.extend(["-i", str(path)])
        filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
    
    # Concatenate video streams only
    v_inputs = "".join([f"[v{i}]" for i in range(len(valid_items))])
    filter_parts.append(f"{v_inputs}concat=n={len(valid_items)}:v=1:a=0[v]")
    
    filter_complex = ";".join(filter_parts)
    
    # Output file
    output_mp4 = out_dir / "combined_video_only.mp4"
    
    # Build FFmpeg command - video only
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
    
    print(f"\nSuccess! Created: {output_mp4}")
    print(f"Clips processed: {len(valid_items)}")
    print("Output: Silent video with AI-optimized sequence")

if __name__ == "__main__":
    main()