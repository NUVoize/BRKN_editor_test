#!/usr/bin/env python3
"""
Enhanced Clip Analyzer - Specifically designed for multi-angle scene detection
Extends your existing analyze_clip.py with camera angle and scene grouping capabilities
"""

import json
import os
import sys
import subprocess
import tempfile
import requests
from pathlib import Path
import base64
from collections import Counter

class EnhancedClipAnalyzer:
   def __init__(self, lmstudio_url="http://localhost:1234/v1/chat/completions", 
             model="InternVL3_5-14B-GGUF"):
        self.lmstudio_url = lmstudio_url
        self.model = model
        
    def extract_analysis_frames(self, video_path, output_dir):
        """Extract multiple frames for better angle/scene analysis"""
        frames = {}
        
        # Get video duration first
        duration_cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
            '-of', 'csv=p=0', str(video_path)
        ]
        
        try:
            duration = float(subprocess.check_output(duration_cmd, text=True).strip())
        except:
            duration = 5.0  # Default
        
        # Extract frames at different points for better analysis
        frame_times = [
            ('start', 0.5),
            ('quarter', duration * 0.25),
            ('middle', duration * 0.5),
            ('three_quarter', duration * 0.75),
            ('end', duration - 0.5)
        ]
        
        for frame_name, time_point in frame_times:
            frame_path = output_dir / f"{Path(video_path).stem}_{frame_name}.jpg"
            
            cmd = [
                'ffmpeg', '-y', '-i', str(video_path),
                '-ss', str(time_point), '-vframes', '1',
                '-q:v', '2', str(frame_path)
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                frames[frame_name] = frame_path
            except subprocess.CalledProcessError as e:
                print(f"Error extracting {frame_name} frame: {e}")
        
        return frames
    
    def analyze_with_vision_model(self, image_path, analysis_type="comprehensive"):
        """Analyze image with LM Studio vision model"""
        
        # Convert image to base64
        with open(image_path, 'rb') as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Specialized prompts for different analysis types
        prompts = {
            "camera_angle": """Analyze this video frame and identify:
1. Camera angle (close-up, medium shot, wide shot, overhead, low angle, side angle)
2. Camera position relative to subject (front, side, behind, above, below)
3. Shot composition (tight, loose, centered, off-center)
4. Camera distance from subject (very close, close, medium, far, very far)

Be specific and technical in your camera analysis.""",

            "scene_context": """Analyze this video frame for scene grouping:
1. Location/setting (bedroom, bathroom, living room, kitchen, outdoor, etc.)
2. Lighting conditions (natural, artificial, dim, bright, colored)
3. Background elements and props
4. Overall scene atmosphere and mood
5. Time of day indicators

Focus on elements that would help group similar scenes together.""",

            "motion_analysis": """Analyze this frame for motion and loop potential:
1. Type of movement visible (if any)
2. Direction and intensity of motion
3. Repetitive action potential
4. Body positioning and posture
5. Action that might loop well

Rate the loop potential from 1-10 and explain why.""",

            "comprehensive": """Analyze this adult video frame comprehensively:

CAMERA & TECHNICAL:
- Camera angle and position
- Shot type and composition
- Lighting quality and direction

SCENE & SETTING:
- Location and environment
- Background elements
- Atmosphere and mood

SUBJECT & ACTION:
- Number of people
- Body positioning
- Type of activity/movement
- Motion direction and intensity

PRODUCTION QUALITY:
- Video quality indicators
- Professional vs amateur
- Aesthetic elements

GROUPING FACTORS:
- What makes this scene unique?
- What elements could group it with similar scenes?
- Loop potential (1-10 rating)

Be detailed but professional in your analysis."""
        }
        
        prompt = prompts.get(analysis_type, prompts["comprehensive"])
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert video analysis AI specializing in adult content categorization for video editing purposes. Provide technical, professional analysis focused on camera work, scene composition, and editing potential. Be direct and detailed."
                },
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1000,
            "stream": False
        }
        
        try:
            response = requests.post(self.lmstudio_url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
        
        except Exception as e:
            print(f"Error in vision analysis: {e}")
            return f"Analysis failed: {str(e)}"
    
    def parse_analysis_response(self, analysis_text):
        """Parse the AI response into structured data"""
        data = {
            'camera_angle': 'unknown',
            'camera_position': 'unknown',
            'shot_type': 'unknown',
            'scene_location': 'unknown',
            'lighting_type': 'unknown',
            'motion_type': 'unknown',
            'loop_potential': 0,
            'scene_group': 'unknown',
            'production_quality': 'unknown',
            'full_analysis': analysis_text
        }
        
        text = analysis_text.lower()
        
        # Extract camera angle
        if any(word in text for word in ['close-up', 'closeup', 'close up']):
            data['camera_angle'] = 'close_up'
        elif any(word in text for word in ['wide shot', 'wide angle', 'wide']):
            data['camera_angle'] = 'wide_shot'
        elif any(word in text for word in ['medium shot', 'medium']):
            data['camera_angle'] = 'medium_shot'
        elif any(word in text for word in ['overhead', 'above', 'top down']):
            data['camera_angle'] = 'overhead'
        elif any(word in text for word in ['low angle', 'below', 'upward']):
            data['camera_angle'] = 'low_angle'
        elif any(word in text for word in ['side', 'profile']):
            data['camera_angle'] = 'side_angle'
        
        # Extract scene location
        locations = ['bedroom', 'bathroom', 'living room', 'kitchen', 'office', 'outdoor']
        for location in locations:
            if location in text:
                data['scene_location'] = location
                break
        
        # Extract lighting
        if any(word in text for word in ['natural', 'daylight', 'window']):
            data['lighting_type'] = 'natural'
        elif any(word in text for word in ['artificial', 'lamp', 'led']):
            data['lighting_type'] = 'artificial'
        elif any(word in text for word in ['dim', 'dark', 'low light']):
            data['lighting_type'] = 'dim'
        elif any(word in text for word in ['bright', 'well lit']):
            data['lighting_type'] = 'bright'
        
        # Extract loop potential score
        import re
        loop_match = re.search(r'loop potential.*?(\d+)', text)
        if loop_match:
            data['loop_potential'] = int(loop_match.group(1))
        
        # Create scene group signature
        data['scene_group'] = f"{data['scene_location']}_{data['lighting_type']}_{data['camera_angle']}"
        
        return data
    
    def analyze_video_comprehensive(self, video_path, meta_dir):
        """Comprehensive analysis of a video file"""
        video_name = Path(video_path).stem
        print(f"Enhanced analysis of: {video_name}")
        
        # Create temp directory for frames
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract multiple frames
            frames = self.extract_analysis_frames(video_path, temp_path)
            
            if not frames:
                print(f"Failed to extract frames from {video_path}")
                return None
            
            # Analyze each frame type
            frame_analyses = {}
            for frame_type, frame_path in frames.items():
                print(f"  Analyzing {frame_type} frame...")
                analysis = self.analyze_with_vision_model(frame_path, "comprehensive")
                frame_analyses[frame_type] = {
                    'raw_analysis': analysis,
                    'parsed_data': self.parse_analysis_response(analysis)
                }
            
            # Combine analyses into final result
            combined_data = self.combine_frame_analyses(frame_analyses, video_path)
            
            # Save enhanced analysis
            output_file = Path(meta_dir) / f"{video_name}.json"
            with open(output_file, 'w') as f:
                json.dump(combined_data, f, indent=2)
            
            print(f"  ✓ Enhanced analysis saved: {output_file}")
            return combined_data
    
    def combine_frame_analyses(self, frame_analyses, video_path):
        """Combine multiple frame analyses into coherent data"""
        
        # Get video duration
        duration_cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
            '-of', 'csv=p=0', str(video_path)
        ]
        
        try:
            duration = float(subprocess.check_output(duration_cmd, text=True).strip())
        except:
            duration = 5.0
        
        # Aggregate data from all frames
        camera_angles = []
        scene_locations = []
        lighting_types = []
        loop_potentials = []
        
        for frame_type, analysis in frame_analyses.items():
            data = analysis['parsed_data']
            camera_angles.append(data['camera_angle'])
            scene_locations.append(data['scene_location'])
            lighting_types.append(data['lighting_type'])
            loop_potentials.append(data['loop_potential'])
        
        # Determine most common values
        def most_common(lst):
            counter = Counter([x for x in lst if x != 'unknown'])
            if counter:
                return counter.most_common(1)[0][0]
            return 'unknown'
        
        # Build final enhanced data structure
        enhanced_data = {
            'video_path': str(video_path),
            'video_name': Path(video_path).stem,
            'duration': duration,
            'camera_analysis': {
                'primary_angle': most_common(camera_angles),
                'angle_changes': len(set(camera_angles)) > 1,
                'all_angles': camera_angles
            },
            'scene_analysis': {
                'location': most_common(scene_locations),
                'lighting': most_common(lighting_types),
                'scene_signature': f"{most_common(scene_locations)}_{most_common(lighting_types)}"
            },
            'editing_analysis': {
                'loop_potential': max(loop_potentials) if loop_potentials else 0,
                'avg_loop_score': sum(loop_potentials) / len(loop_potentials) if loop_potentials else 0,
                'angle_variety': len(set(camera_angles)),
                'scene_consistency': len(set(scene_locations)) == 1
            },
            'frame_by_frame': frame_analyses,
            'grouping': {
                'scene_group': f"{most_common(scene_locations)}_{most_common(lighting_types)}",
                'angle_group': most_common(camera_angles),
                'quality_group': self.assess_production_quality(frame_analyses)
            }
        }
        
        return enhanced_data
    
    def assess_production_quality(self, frame_analyses):
        """Assess production quality from frame analyses"""
        # Simple quality assessment based on analysis text
        quality_indicators = []
        
        for analysis in frame_analyses.values():
            text = analysis['raw_analysis'].lower()
            if any(word in text for word in ['professional', 'high quality', 'well lit']):
                quality_indicators.append('high')
            elif any(word in text for word in ['amateur', 'low quality', 'poor']):
                quality_indicators.append('low')
            else:
                quality_indicators.append('medium')
        
        counter = Counter(quality_indicators)
        return counter.most_common(1)[0][0] if counter else 'medium'

def main():
    if len(sys.argv) < 3:
        print("Usage: python enhanced_clip_analyzer.py <video_file> <meta_dir>")
        print("   or: python enhanced_clip_analyzer.py <video_dir> <meta_dir> --batch")
        print("\nExample:")
        print("  python enhanced_clip_analyzer.py E:\\n8n-docker\\videos_in\\clip.mp4 E:\\n8n-docker\\data\\meta")
        print("  python enhanced_clip_analyzer.py E:\\n8n-docker\\videos_in E:\\n8n-docker\\data\\meta --batch")
        sys.exit(1)
    
    video_input = sys.argv[1]
    meta_dir = sys.argv[2]
    batch_mode = len(sys.argv) > 3 and sys.argv[3] == '--batch'
    
    # Create meta directory if it doesn't exist
    Path(meta_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize analyzer
    analyzer = EnhancedClipAnalyzer()
    
    if batch_mode:
        # Process all videos in directory
        video_dir = Path(video_input)
        video_files = list(video_dir.glob('*.mp4')) + list(video_dir.glob('*.mov')) + list(video_dir.glob('*.avi'))
        
        print(f"Processing {len(video_files)} videos in batch mode...")
        
        for video_file in video_files:
            try:
                analyzer.analyze_video_comprehensive(video_file, meta_dir)
            except Exception as e:
                print(f"Error processing {video_file}: {e}")
        
        print(f"\nBatch processing complete. {len(video_files)} videos analyzed.")
    
    else:
        # Process single video
        video_file = Path(video_input)
        if not video_file.exists():
            print(f"Video file not found: {video_file}")
            sys.exit(1)
        
        try:
            result = analyzer.analyze_video_comprehensive(video_file, meta_dir)
            if result:
                print("\nAnalysis Summary:")
                print(f"Camera Angle: {result['camera_analysis']['primary_angle']}")
                print(f"Scene Location: {result['scene_analysis']['location']}")
                print(f"Lighting: {result['scene_analysis']['lighting']}")
                print(f"Loop Potential: {result['editing_analysis']['loop_potential']}/10")
                print(f"Scene Group: {result['grouping']['scene_group']}")
        except Exception as e:
            print(f"Error processing video: {e}")

if __name__ == "__main__":
    main()