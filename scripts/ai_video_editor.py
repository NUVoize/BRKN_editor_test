#!/usr/bin/env python3
"""
AI Video Editor - Multi-Angle Scene Builder
Standalone tool - reads original videos from videos_in with natural audio
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from collections import defaultdict, deque

class AIVideoEditor:
    def __init__(self, meta_dir, videos_in_dir, output_dir):
        self.meta_dir = Path(meta_dir)
        self.videos_in_dir = Path(videos_in_dir) 
        self.output_dir = Path(output_dir)
        self.clips_data = {}
        self.scenes = defaultdict(list)
        self.loops = {}
        
    def load_clip_analysis(self):
        """Load all clip analysis JSON files"""
        print("Loading clip analysis data...")
        
        for json_file in self.meta_dir.glob("*.json"):
            if json_file.name in ['manifest.json', 'smart_manifest.json']:
                continue
                
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    clip_name = json_file.stem
                    
                    # Check if corresponding video exists
                    video_file = self.videos_in_dir / f"{clip_name}.mp4"
                    if video_file.exists():
                        self.clips_data[clip_name] = data
                        print(f"Loaded: {clip_name}")
                    else:
                        print(f"Skipped: {clip_name} (no video file)")
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        print(f"Loaded {len(self.clips_data)} clips with videos")
        return len(self.clips_data) > 0
    
    def analyze_scenes_and_angles(self):
        """Group clips by scenes and detect camera angles"""
        print("Analyzing scenes and camera angles...")
        
        for clip_name, data in self.clips_data.items():
            # Extract scene characteristics
            scene_key = self.get_scene_signature(data)
            self.scenes[scene_key].append(clip_name)
            
        # Print analysis results
        print(f"\nFound {len(self.scenes)} distinct scenes:")
        for scene, clips in self.scenes.items():
            print(f"  {scene}: {len(clips)} clips")
    
    def get_scene_signature(self, data):
        """Create a scene signature based on AI analysis"""
        try:
            # Use your existing analysis format
            scene_type = str(data.get('scene_type', 'unknown'))
            lighting = str(data.get('lighting', 'unknown'))
            setting = str(data.get('setting', 'unknown'))
            
            signature = f"{scene_type}_{lighting}_{setting}"
            return signature.lower().replace(' ', '_').replace(',', '').replace('(', '').replace(')', '')
        except:
            return "unknown_scene"
    
    def detect_loop_candidates(self):
        """Find clips good for looping"""
        print("Detecting loop candidates...")
        
        for clip_name, data in self.clips_data.items():
            # Look for repetitive motion indicators
            motion = str(data.get('motion', '')).lower()
            action = str(data.get('action', '')).lower()
            
            score = 0
            if any(word in motion + action for word in ['repetitive', 'rhythmic', 'steady', 'consistent']):
                score += 0.5
            if any(word in motion + action for word in ['thrust', 'bounce', 'rock', 'grind']):
                score += 0.3
                
            if score > 0.4:
                self.loops[clip_name] = {
                    'score': score,
                    'reason': 'Repetitive motion detected'
                }
        
        print(f"Found {len(self.loops)} loop candidates")
    
    def build_multi_angle_scene(self, scene_name, target_duration=30.0):
        """Build a scene using multiple clips"""
        if scene_name not in self.scenes:
            print(f"Scene '{scene_name}' not found")
            return None, None
        
        scene_clips = self.scenes[scene_name][:6]  # Limit to 6 clips for performance
        print(f"\nBuilding multi-angle scene '{scene_name}' with {len(scene_clips)} clips...")
        
        return self.generate_scene_command(scene_clips, scene_name, target_duration)
    
    def generate_scene_command(self, clips, scene_name, duration):
        """Generate FFmpeg command for multi-angle scene"""
        inputs = []
        filter_parts = []
        concat_inputs = []
        
        clip_duration = duration / len(clips)  # Equal time per clip
        
        for i, clip_name in enumerate(clips):
            # Input file with original audio from videos_in
            video_path = self.videos_in_dir / f"{clip_name}.mp4"
            inputs.extend(['-i', str(video_path)])
            
            # Trim each clip (skip first 0.5s, use 4s)
            filter_parts.append(f"[{i}:v]trim=start=0.5:duration=4.0[v{i}]")
            filter_parts.append(f"[{i}:a]atrim=start=0.5:duration=4.0[a{i}]")
            
            concat_inputs.extend([f"[v{i}]", f"[a{i}]"])
            print(f"  Cut {i+1}: {clip_name} (4.0s)")
        
        # Concatenate all clips
        n_segments = len(clips)
        concat_filter = f"{''.join(concat_inputs)}concat=n={n_segments}:v=1:a=1[outv][outa]"
        filter_parts.append(concat_filter)
        
        filter_complex = ';'.join(filter_parts)
        
        # Output to videos_out
        output_path = self.output_dir / f"scene_{scene_name}.mp4"
        
        command = [
            'ffmpeg', '-y'
        ] + inputs + [
            '-filter_complex', filter_complex,
            '-map', '[outv]', '-map', '[outa]',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            str(output_path)
        ]
        
        return command, output_path
    
    def create_loop(self, clip_name, loop_duration=15.0):
        """Create a seamless loop"""
        video_path = self.videos_in_dir / f"{clip_name}.mp4"
        output_path = self.output_dir / f"loop_{clip_name}.mp4"
        
        command = [
            'ffmpeg', '-y',
            '-stream_loop', '2',  # Loop 3 times total
            '-i', str(video_path),
            '-t', str(loop_duration),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            str(output_path)
        ]
        
        return command, output_path
    
    def run_ffmpeg(self, command, description):
        """Execute FFmpeg command"""
        print(f"\n{description}")
        
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ {description} completed successfully")
                return True
            else:
                print(f"✗ FFmpeg error:")
                print(result.stderr[:500])  # Show first 500 chars of error
                return False
        except Exception as e:
            print(f"✗ Command failed: {e}")
            return False
    
    def auto_build_scenes(self):
        """Automatically build scenes"""
        print(f"\n=== Auto-building scenes ===")
        
        # Build each scene
        for scene_name, clips in self.scenes.items():
            if len(clips) >= 2:  # Need at least 2 clips
                command, output_path = self.build_multi_angle_scene(scene_name, 24.0)
                if command:
                    self.run_ffmpeg(command, f"Building scene: {scene_name}")
        
        # Create loops
        print(f"\n=== Creating loops ===")
        for clip_name in list(self.loops.keys())[:3]:  # Max 3 loops
            command, output_path = self.create_loop(clip_name)
            if command:
                self.run_ffmpeg(command, f"Creating loop: {clip_name}")
    
    def interactive_menu(self):
        """Interactive menu"""
        while True:
            print("\nOptions:")
            print("1. List available scenes")
            print("2. Build multi-angle scene")
            print("3. Create seamless loop")
            print("4. Auto-build scenes")
            print("5. Exit")
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                print("\nAvailable scenes:")
                for i, (scene, clips) in enumerate(self.scenes.items(), 1):
                    print(f"{i}. {scene} ({len(clips)} clips)")
            
            elif choice == '2':
                scene_list = list(self.scenes.keys())
                if scene_list:
                    print("\nAvailable scenes:")
                    for i, scene in enumerate(scene_list, 1):
                        print(f"{i}. {scene} ({len(self.scenes[scene])} clips)")
                    
                    try:
                        scene_idx = int(input("Select scene number: ")) - 1
                        if 0 <= scene_idx < len(scene_list):
                            scene_name = scene_list[scene_idx]
                            duration = float(input("Target duration (seconds, default 24): ") or 24)
                            
                            command, output_path = self.build_multi_angle_scene(scene_name, duration)
                            if command and self.run_ffmpeg(command, f"Building scene {scene_name}"):
                                print(f"Scene created: {output_path}")
                    except (ValueError, IndexError):
                        print("Invalid selection")
            
            elif choice == '3':
                clip_name = input("Enter clip name for loop: ").strip()
                duration = float(input("Loop duration (seconds, default 15): ") or 15)
                
                command, output_path = self.create_loop(clip_name, duration)
                if command and self.run_ffmpeg(command, f"Creating loop from {clip_name}"):
                    print(f"Loop created: {output_path}")
            
            elif choice == '4':
                self.auto_build_scenes()
            
            elif choice == '5':
                break

def main():
    if len(sys.argv) != 4:
        print("Usage: python ai_video_editor.py <meta_dir> <videos_in_dir> <output_dir>")
        print("Example: python ai_video_editor.py E:\\n8n-docker\\data\\meta E:\\n8n_docker_strick\\videos_in E:\\n8n-docker\\videos_out")
        sys.exit(1)
    
    meta_dir = sys.argv[1]
    videos_in_dir = sys.argv[2] 
    output_dir = sys.argv[3]
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    editor = AIVideoEditor(meta_dir, videos_in_dir, output_dir)
    
    if not editor.load_clip_analysis():
        print("No clip analysis data found.")
        sys.exit(1)
    
    editor.analyze_scenes_and_angles()
    editor.detect_loop_candidates()
    editor.interactive_menu()

if __name__ == "__main__":
    main()