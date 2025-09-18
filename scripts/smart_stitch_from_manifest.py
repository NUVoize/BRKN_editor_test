#!/usr/bin/env python3
"""
smart_stitch_from_manifest.py
Enhanced version that handles smart_manifest.json with intelligent transitions
Automatically detects and uses AI-optimized sequencing
"""

import json, os, subprocess, sys
from pathlib import Path

FFMPEG = os.getenv("FFMPEG", "ffmpeg")

def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)

def build_transition_filter(items, transitions):
    """Build FFmpeg filter for intelligent transitions"""
    filter_parts = []
    
    # Process each input clip
    for i, item in enumerate(items):
        filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}];[{i}:a]asetpts=N/SR/TB[a{i}]")
    
    if not transitions:
        # No transitions - simple concatenation
        v_inputs = "".join([f"[v{i}]" for i in range(len(items))])
        a_inputs = "".join([f"[a{i}]" for i in range(len(items))])
        filter_parts.append(f"{v_inputs}{a_inputs}concat=n={len(items)}:v=1:a=1[v][a]")
        return ";".join(filter_parts)
    
    # Build smart transition chain
    current_v = "v0"
    current_a = "a0"
    
    for i, transition in enumerate(transitions):
        next_idx = i + 1
        transition_type = transition.get("type", "cut")
        duration = float(transition.get("duration", 0.5))
        
        if transition_type == "crossfade" and duration > 0:
            # Crossfade transition
            filter_parts.append(
                f"[{current_v}][v{next_idx}]xfade=transition=fade:duration={duration}[vx{i}]"
            )
            filter_parts.append(
                f"[{current_a}][a{next_idx}]acrossfade=duration={duration}[ax{i}]"
            )
            current_v = f"vx{i}"
            current_a = f"ax{i}"
            
        elif transition_type == "fade_black" and duration > 0:
            # Fade to black transition - simplified to avoid FFmpeg syntax issues
            filter_parts.extend([
                f"[{current_v}]fade=t=out:d={duration}[vfo{i}]",
                f"[{current_a}]afade=t=out:d={duration}[afo{i}]",
                f"[v{next_idx}]fade=t=in:d={duration}[vfi{i}]",
                f"[a{next_idx}]afade=t=in:d={duration}[afi{i}]",
                f"[vfo{i}][vfi{i}]concat=n=2:v=1:a=0[vx{i}]",
                f"[afo{i}][afi{i}]concat=n=2:v=0:a=1[ax{i}]"
            ])
            current_v = f"vx{i}"
            current_a = f"ax{i}"
            
        else:
            # Direct cut
            filter_parts.extend([
                f"[{current_v}][v{next_idx}]concat=n=2:v=1:a=0[vx{i}]",
                f"[{current_a}][a{next_idx}]concat=n=2:v=0:a=1[ax{i}]"
            ])
            current_v = f"vx{i}"
            current_a = f"ax{i}"
    
    # Final output
    filter_parts.extend([f"[{current_v}]null[v]", f"[{current_a}]anull[a]"])
    return ";".join(filter_parts)

def main():
    if len(sys.argv) < 2:
        die(f"Usage: {sys.argv[0]} <OUT_DIR>")
    
    out_dir = Path(sys.argv[1]).resolve()
    
    # Try smart manifest first, then regular manifest
    smart_manifest = out_dir / "smart_manifest.json"
    regular_manifest = out_dir / "manifest.json"
    
    if smart_manifest.exists():
        manifest_path = smart_manifest
        print("Using smart manifest with AI-optimized transitions...")
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
    
    # Parse manifest format
    if isinstance(manifest_data, list):
        # Old format
        items = manifest_data
        transitions = []
        print("Regular manifest format detected")
    else:
        # Smart format
        items = manifest_data.get("items", [])
        transitions = manifest_data.get("transitions", [])
        print(f"Smart manifest format detected: {len(transitions)} transitions")
    
    if not items:
        die("No items found in manifest")
    
    # Validate files exist
    valid_items = []
    missing = []
    
    for item in items:
        path = item.get("path")
        if not path or not os.path.exists(path):
            missing.append(path or "unknown")
        else:
            valid_items.append(item)
    
    if missing:
        print(f"Warning: {len(missing)} missing files:")
        for m in missing[:5]:
            print(f"  - {m}")
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more")
    
    if not valid_items:
        die("No valid files found")
    
    print(f"Processing {len(valid_items)} clips...")
    
    # Prepare FFmpeg inputs
    inputs = []
    for item in valid_items:
        inputs.extend(["-i", str(item["path"])])
    
    # Build filter complex
    if transitions and manifest_path == smart_manifest:
        print("Applying intelligent transitions:")
        for i, t in enumerate(transitions[:5]):  # Show first 5
            score = t.get('score', 0)
            print(f"  {t['from_clip']} → {t['to_clip']}: {t['type']} (score: {score:.3f})")
        if len(transitions) > 5:
            print(f"  ... and {len(transitions) - 5} more")
        
        filter_complex = build_transition_filter(valid_items, transitions)
    else:
        print("Using simple concatenation...")
        v_inputs = "".join([f"[{i}:v]setpts=PTS-STARTPTS[v{i}];" for i in range(len(valid_items))])
        a_inputs = "".join([f"[{i}:a]asetpts=N/SR/TB[a{i}];" for i in range(len(valid_items))])
        concat_v = "".join([f"[v{i}]" for i in range(len(valid_items))])
        concat_a = "".join([f"[a{i}]" for i in range(len(valid_items))])
        filter_complex = f"{v_inputs}{a_inputs}{concat_v}{concat_a}concat=n={len(valid_items)}:v=1:a=1[v][a]"
    
    # Output file
    output_name = "combined_smart.mp4" if manifest_path == smart_manifest else "combined.mp4"
    output_mp4 = out_dir / output_name
    
    # Build FFmpeg command
    cmd = [
        FFMPEG, "-y"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(output_mp4)
    ]
    
    print(f"\nGenerating: {output_mp4.name}")
    
    # Execute FFmpeg
    proc = subprocess.run(cmd, text=True, capture_output=True)
    
    if proc.returncode != 0:
        print("FFmpeg error:")
        print(proc.stderr[-1000:])  # Last 1000 chars of error
        die("FFmpeg failed", proc.returncode)
    
    print(f"\nSuccess! Created: {output_mp4}")
    
    # Summary
    total_duration = sum(item.get("t1", 5.0) - item.get("t0", 0.0) for item in valid_items)
    print(f"\nSummary:")
    print(f"  Clips: {len(valid_items)}")
    print(f"  Duration: ~{total_duration:.1f}s")
    
    if transitions:
        avg_score = sum(t.get('score', 0) for t in transitions) / len(transitions)
        transition_counts = {}
        for t in transitions:
            t_type = t.get('type', 'unknown')
            transition_counts[t_type] = transition_counts.get(t_type, 0) + 1
        
        print(f"  Avg transition quality: {avg_score:.3f}")
        for t_type, count in transition_counts.items():
            print(f"  {t_type} transitions: {count}")

if __name__ == "__main__":
    main()