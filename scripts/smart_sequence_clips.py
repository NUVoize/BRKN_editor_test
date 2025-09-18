# FILE 1: smart_sequence_clips.py
# (Use the code from the first artifact I provided earlier)

#!/usr/bin/env python3
"""
smart_sequence_clips.py
Intelligently orders and transitions video clips based on AI analysis.
Reads metadata JSONs from analyze_clip.py and creates optimized manifest.
"""

import os, sys, json, glob
from pathlib import Path
import numpy as np
from typing import List, Dict, Tuple

class ClipAnalyzer:
    def __init__(self, meta_dir: Path):
        self.meta_dir = meta_dir
        self.clips = []
        self.load_metadata()
    
    def load_metadata(self):
        """Load all clip metadata from analyze_clip.py outputs"""
        json_files = sorted(glob.glob(str(self.meta_dir / "*.json")))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate structure from analyze_clip.py
                if 'start' in data and 'end' in data and 'file' in data:
                    self.clips.append({
                        'file': data['file'],
                        'path': data.get('file'),  # Full path if available
                        'start_frame': data['start'],
                        'end_frame': data['end'],
                        'base': data.get('base', Path(json_file).stem)
                    })
            except Exception as e:
                print(f"Warning: Could not load {json_file}: {e}")
        
        print(f"Loaded {len(self.clips)} clips with AI analysis")
    
    def calculate_transition_score(self, clip_a: Dict, clip_b: Dict) -> float:
        """Calculate how well clip A's end transitions to clip B's start"""
        end_a = clip_a['end_frame']
        start_b = clip_b['start_frame']
        
        score = 0.0
        
        # 1. Subject continuity (30% weight)
        if end_a.get('subject', '') == start_b.get('subject', ''):
            score += 0.3
        elif self._similar_subjects(end_a.get('subject', ''), start_b.get('subject', '')):
            score += 0.15
        
        # 2. Scene type match (25% weight)
        if end_a.get('scene_type', '') == start_b.get('scene_type', ''):
            score += 0.25
        
        # 3. Lighting continuity (20% weight)
        if end_a.get('lighting', '') == start_b.get('lighting', ''):
            score += 0.2
        elif self._compatible_lighting(end_a.get('lighting', ''), start_b.get('lighting', '')):
            score += 0.1
        
        # 4. Motion compatibility (15% weight)
        motion_score = self._motion_compatibility(end_a.get('motion', ''), start_b.get('motion', ''))
        score += motion_score * 0.15
        
        # 5. Color harmony (10% weight)
        color_score = self._color_harmony(
            end_a.get('dominant_colors', []), 
            start_b.get('dominant_colors', [])
        )
        score += color_score * 0.1
        
        return min(1.0, score)
    
    def _similar_subjects(self, subj_a: str, subj_b: str) -> bool:
        if not subj_a or not subj_b:
            return False
        words_a = set(subj_a.lower().split())
        words_b = set(subj_b.lower().split())
        return len(words_a & words_b) > 0
    
    def _compatible_lighting(self, light_a: str, light_b: str) -> bool:
        bright = {'bright', 'daylight', 'sunny', 'well-lit'}
        dim = {'dim', 'dark', 'low-light', 'evening', 'night'}
        
        if light_a in bright and light_b in bright:
            return True
        if light_a in dim and light_b in dim:
            return True
        return False
    
    def _motion_compatibility(self, motion_a: str, motion_b: str) -> float:
        if not motion_a or not motion_b:
            return 0.5
        if motion_a == motion_b:
            return 1.0
        
        slow_motions = {'slow', 'gentle', 'calm', 'still', 'steady'}
        fast_motions = {'fast', 'quick', 'rapid', 'dynamic', 'energetic'}
        
        if motion_a in slow_motions and motion_b in slow_motions:
            return 0.8
        if motion_a in fast_motions and motion_b in fast_motions:
            return 0.8
        if (motion_a in slow_motions and motion_b in fast_motions) or \
           (motion_a in fast_motions and motion_b in slow_motions):
            return 0.2
        return 0.5
    
    def _color_harmony(self, colors_a: List[str], colors_b: List[str]) -> float:
        if not colors_a or not colors_b:
            return 0.5
        matches = len(set(colors_a) & set(colors_b))
        max_possible = min(len(colors_a), len(colors_b))
        if max_possible == 0:
            return 0.5
        return matches / max_possible
    
    def find_optimal_sequence(self) -> List[Dict]:
        if len(self.clips) <= 1:
            return self.clips
        
        sequence = [self.clips[0]]
        remaining = self.clips[1:].copy()
        
        while remaining:
            current_clip = sequence[-1]
            best_score = -1
            best_clip = None
            best_idx = -1
            
            for i, candidate in enumerate(remaining):
                score = self.calculate_transition_score(current_clip, candidate)
                if score > best_score:
                    best_score = score
                    best_clip = candidate
                    best_idx = i
            
            if best_clip:
                sequence.append(best_clip)
                remaining.pop(best_idx)
                print(f"Added {best_clip['base']} (transition score: {best_score:.3f})")
            else:
                sequence.append(remaining.pop(0))
        
        return sequence
    
    def generate_transitions(self, sequence: List[Dict]) -> List[Dict]:
        transitions = []
        
        for i in range(len(sequence) - 1):
            current = sequence[i]
            next_clip = sequence[i + 1]
            score = self.calculate_transition_score(current, next_clip)
            
            if score > 0.8:
                transition_type = "cut"
                duration = 0.0
            elif score > 0.5:
                transition_type = "crossfade"
                duration = 0.5
            else:
                transition_type = "fade_black"
                duration = 0.3
            
            transitions.append({
                "from_clip": current['base'],
                "to_clip": next_clip['base'],
                "type": transition_type,
                "duration": duration,
                "score": score
            })
        
        return transitions
    
    def create_smart_manifest(self, out_dir: Path):
        print("Finding optimal clip sequence...")
        optimal_sequence = self.find_optimal_sequence()
        
        print("Generating transitions...")
        transitions = self.generate_transitions(optimal_sequence)
        
        manifest_items = []
        current_time = 0.0
        
        for i, clip in enumerate(optimal_sequence):
            clip_duration = 5.0
            
            if i > 0:
                transition = transitions[i-1]
                if transition['type'] == 'crossfade':
                    current_time -= transition['duration']
            
            manifest_items.append({
                "path": str(Path(clip['path']).resolve()) if clip['path'] else clip['file'],
                "t0": current_time,
                "t1": current_time + clip_duration,
                "base": clip['base'],
                "transition_in": transitions[i-1] if i > 0 else None
            })
            
            current_time += clip_duration
        
        manifest_path = out_dir / "smart_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump({
                "version": "smart_v1",
                "items": manifest_items,
                "transitions": transitions,
                "total_duration": current_time,
                "optimization_summary": {
                    "total_clips": len(optimal_sequence),
                    "avg_transition_score": np.mean([t['score'] for t in transitions]) if transitions else 0.0
                }
            }, f, indent=2)
        
        print(f"\nSmart manifest created: {manifest_path}")
        print(f"Optimization summary:")
        print(f"  - Total clips: {len(optimal_sequence)}")
        if transitions:
            avg_score = np.mean([t['score'] for t in transitions])
            print(f"  - Average transition score: {avg_score:.3f}")
        
        return manifest_path

def main():
    if len(sys.argv) < 3:
        print("Usage: smart_sequence_clips.py <META_DIR> <OUT_DIR>")
        sys.exit(1)
    
    meta_dir = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not meta_dir.exists():
        print(f"Error: Meta directory not found: {meta_dir}")
        sys.exit(1)
    
    analyzer = ClipAnalyzer(meta_dir)
    
    if not analyzer.clips:
        print("No clips found with AI analysis. Run analyze_clip.py first.")
        sys.exit(1)
    
    manifest_path = analyzer.create_smart_manifest(out_dir)
    print(f"\nNext step: Use video_only_stitcher.py {out_dir}")

if __name__ == "__main__":
    main()
