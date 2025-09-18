#!/usr/bin/env python3
"""
simple_cuts_stitcher.py
AI-optimized sequencing with clean cuts only. No crossfades, no transitions.
Supports trimming clips to remove poor transition frames.
"""

import json, os, subprocess, sys
from pathlib import Path

FFMPEG = os.getenv("FFMPEG", "ffmpeg")
TRIM_POOR_TRANSITIONS = True  # Set to True to trim clips with low transition scores
POOR_SCORE_THRESHOLD = 0.5    # Clips with scores below this get trimmed

def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)

def calculate_trim_seconds(transition_score):
    """Calculate how many seconds to trim from clip ends based on transition score"""
    if transition_score >= POOR_SCORE_THRESHOLD:
        return 0.0  # No trimming for good transitions
    
    # Trim more for worse transitions (max 1 second)
    trim_amount = (POOR_SCORE_THRESHOLD - transition_score) * 2.0
    return min(1.0, trim_amount)

def main():
    if len(sys.argv) < 2:
        die(f"Usage: {sys.argv[0]} <OUT_DIR>")
    
    out_dir = Path(sys.argv[1]).resolve()
    
    # Try smart manifest first
    smart_manifest = out_dir / "smart_manifest.json"
    regular_manifest = out_dir / "manifest.json"
    
    if smart_manifest.exists():
        manifest_path = smart_manifest
        print("Using AI-optimized sequence with clean cuts...")
    elif regular_manifest.exists():
        manifest_path = regular_manifest
        print("Using regular manifest...")
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
        is_smart = False
    else:
        items = manifest_data.get("items", [])
        transitions = manifest_data.get("transitions", [])
        is_smart = True
    
    if not items:
        die("No items found in manifest")
    
    # Validate files
    valid_items = []
    missing = []
    
    for item in items:
        path = item.get("path")
        if not path or not os.path.exists(path):
            missing.append(path or "unknown")
        else:
            valid_items.append(item)
    
    if missing:
        print(f"Warning: {len(missing)} missing files (skipping)")
    
    if not valid_items:
        die("No valid files found")
    
    print(f"Processing {len(valid_items)} clips with clean cuts...")
    
    # Show transition info if available
    if is_smart and transitions:
        print("Transition quality:")
        avg_score = sum(t.get('score', 0) for t in transitions) / len(transitions)
        print(f"  Average score: {avg_score:.3f}")
        
        poor_transitions = [t for t in transitions if t.get('score', 0) < POOR_SCORE_THRESHOLD]
        if poor_transitions and TRIM_POOR_TRANSITIONS:
            print(f"  {len(poor_transitions)} poor transitions will be trimmed")
    
    # Build FFmpeg inputs and filter
    inputs = []
    filter_parts = []
    
    for i, item in enumerate(valid_items):
        path = item.get("path")
        inputs.extend(["-i", str(path)])
        
        # Calculate trimming if this is a smart manifest
        trim_end = 0.0
        if is_smart and transitions and i < len(transitions) and TRIM_POOR_TRANSITIONS:
            transition_score = transitions[i].get('score', 1.0)
            trim_end = calculate_trim_seconds(transition_score)
        
        # Create filter for this clip
        if trim_end > 0:
            # Trim the end of clips with poor transition scores
            # Use duration-based trimming instead of end_offset
            clip_duration = item.get("t1", 5.0) - item.get("t0", 0.0)
            new_duration = max(1.0, clip_duration - trim_end)  # Minimum 1 second
            filter_parts.append(f"[{i}:v]trim=duration={new_duration},setpts=PTS-STARTPTS[v{i}]")
            filter_parts.append(f"[{i}:a]atrim=duration={new_duration},asetpts=N/SR/TB[a{i}]")
            print(f"  Trimming {trim_end:.1f}s from end of {Path(path).name}")
        else:
            # No trimming
            filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
            filter_parts.append(f"[{i}:a]asetpts=N/SR/TB[a{i}]")
    
    # Simple concatenation - video only, clean cuts
    v_concat = "".join([f"[v{i}]" for i in range(len(valid_items))])
    filter_parts.append(f"{v_concat}concat=n={len(valid_items)}:v=1:a=0[v]")
    
    filter_complex = ";".join(filter_parts)
    
    # Output file
    output_name = "combined_cuts.mp4" if is_smart else "combined.mp4"
    output_mp4 = out_dir / output_name
    
    # Build command (video only)
    cmd = [
        FFMPEG, "-y"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        str(output_mp4)
    ]
    
    print(f"\nGenerating: {output_mp4.name}")
    
    # Execute
    proc = subprocess.run(cmd, text=True, capture_output=True)
    
    if proc.returncode != 0:
        print("FFmpeg error:")
        print(proc.stderr[-1000:])
        die("FFmpeg failed", proc.returncode)
    
    print(f"\nSuccess! Created: {output_mp4}")
    
    # Summary
    total_duration = sum(item.get("t1", 5.0) - item.get("t0", 0.0) for item in valid_items)
    print(f"\nSummary:")
    print(f"  Clips: {len(valid_items)}")
    print(f"  Estimated duration: ~{total_duration:.1f}s")
    print(f"  Transitions: Clean cuts only")
    
    if is_smart and transitions:
        trimmed_clips = sum(1 for i, t in enumerate(transitions) 
                          if i < len(valid_items) and t.get('score', 1.0) < POOR_SCORE_THRESHOLD)
        if trimmed_clips > 0:
            print(f"  Trimmed clips: {trimmed_clips}")

if __name__ == "__main__":
    main()