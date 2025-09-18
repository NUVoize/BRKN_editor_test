#!/usr/bin/env python3
"""
enhanced_procedural_audio_generator.py
Advanced procedural audio generation using formant synthesis, granular synthesis,
and physics-based sound modeling for more realistic intimate audio content.
"""

import json, os, subprocess, sys
from pathlib import Path
import numpy as np
import random
from scipy import signal
from scipy.io.wavfile import write

# Audio generation parameters
SAMPLE_RATE = 44100
BIT_DEPTH = 16

def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)

def apply_envelope(audio, attack=0.1, decay=0.2, sustain=0.7, release=0.3):
    """Apply ADSR envelope to audio"""
    if len(audio) == 0:
        return audio
    
    samples = len(audio)
    envelope = np.ones(samples)
    
    # Attack
    attack_samples = int(attack * samples)
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    
    # Decay
    decay_samples = int(decay * samples)
    if decay_samples > 0:
        start_idx = attack_samples
        end_idx = min(start_idx + decay_samples, samples)
        if end_idx > start_idx:
            envelope[start_idx:end_idx] = np.linspace(1, sustain, end_idx - start_idx)
    
    # Sustain (constant level)
    sustain_start = attack_samples + decay_samples
    release_samples = int(release * samples)
    sustain_end = max(sustain_start, samples - release_samples)
    if sustain_end > sustain_start:
        envelope[sustain_start:sustain_end] = sustain
    
    # Release
    if release_samples > 0 and sustain_end < samples:
        envelope[sustain_end:] = np.linspace(sustain, 0, samples - sustain_end)
    
    return audio * envelope

def generate_formant_vocal(duration, intensity=0.5, formants=None):
    """Generate realistic vocal sounds using formant synthesis"""
    if formants is None:
        # Default formant frequencies for natural vocal sounds
        formants = [
            (220, 1200, 2500),  # Base formants
            (180, 1000, 2200),  # Variation 1
            (250, 1400, 2800)   # Variation 2
        ]
    
    samples = int(duration * SAMPLE_RATE)
    audio = np.zeros(samples)
    
    # Generate vocal events with natural timing
    current_pos = 0
    while current_pos < samples:
        # Vocal event duration
        event_duration = 0.3 + random.uniform(0, 0.8) + (intensity * 0.5)
        event_samples = int(event_duration * SAMPLE_RATE)
        
        if current_pos + event_samples > samples:
            event_samples = samples - current_pos
        
        if event_samples > 0:
            # Choose random formant set
            f1, f2, f3 = random.choice(formants)
            
            # Base frequency with natural variation
            base_freq = 80 + (intensity * 60) + random.uniform(-10, 10)
            
            # Create time array for this event
            t = np.linspace(0, event_duration, event_samples, False)
            
            # Generate fundamental with vibrato
            vibrato_rate = 3 + random.uniform(0, 4)
            vibrato_depth = 0.05 + (intensity * 0.1)
            freq_modulated = base_freq * (1 + vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t))
            
            # Generate fundamental
            fundamental = np.sin(2 * np.pi * freq_modulated * t)
            
            # Add formants using bandpass filters
            vocal_sound = np.zeros(event_samples)
            
            # First formant (strongest)
            formant1 = signal.lfilter(*signal.butter(4, [f1-100, f1+100], btype='band', fs=SAMPLE_RATE), fundamental)
            vocal_sound += 0.6 * formant1
            
            # Second formant
            formant2 = signal.lfilter(*signal.butter(4, [f2-150, f2+150], btype='band', fs=SAMPLE_RATE), fundamental)
            vocal_sound += 0.4 * formant2
            
            # Third formant (weaker)
            formant3 = signal.lfilter(*signal.butter(4, [f3-200, f3+200], btype='band', fs=SAMPLE_RATE), fundamental)
            vocal_sound += 0.2 * formant3
            
            # Apply natural envelope
            vocal_sound = apply_envelope(vocal_sound, 
                                       attack=0.05 + random.uniform(0, 0.1),
                                       decay=0.1 + random.uniform(0, 0.2),
                                       sustain=0.6 + random.uniform(-0.2, 0.2),
                                       release=0.2 + random.uniform(0, 0.3))
            
            # Scale by intensity
            vocal_sound *= 0.15 * intensity
            
            # Add to main audio
            audio[current_pos:current_pos + event_samples] += vocal_sound
        
        # Add pause between events
        pause_duration = 0.5 + random.uniform(0, 1.5) + (1.0 / max(intensity, 0.2))
        pause_samples = int(pause_duration * SAMPLE_RATE)
        current_pos += event_samples + pause_samples
    
    return audio

def generate_granular_texture(duration, grain_size=0.05, density=0.7, intensity=0.5):
    """Generate texture using granular synthesis"""
    samples = int(duration * SAMPLE_RATE)
    audio = np.zeros(samples)
    
    grain_samples = int(grain_size * SAMPLE_RATE)
    grains_per_second = density * 20 * intensity
    
    total_grains = int(duration * grains_per_second)
    
    for _ in range(total_grains):
        # Random position
        pos = random.randint(0, max(1, samples - grain_samples))
        
        # Generate grain
        if grain_samples > 0:
            # Random frequency for texture
            freq = 60 + random.uniform(0, 200) + (intensity * 100)
            
            t = np.linspace(0, grain_size, grain_samples, False)
            grain = np.sin(2 * np.pi * freq * t)
            
            # Apply window to grain
            window = np.hanning(grain_samples)
            grain *= window
            
            # Random amplitude
            amp = 0.05 * intensity * random.uniform(0.3, 1.0)
            grain *= amp
            
            # Add to audio
            end_pos = min(pos + grain_samples, samples)
            grain_trimmed = grain[:end_pos - pos]
            audio[pos:end_pos] += grain_trimmed
    
    return audio

def generate_contact_physics(duration, contact_rate=2.0, intensity=0.5, contact_type="soft"):
    """Generate contact sounds using physics-based modeling"""
    samples = int(duration * SAMPLE_RATE)
    audio = np.zeros(samples)
    
    contacts_per_second = contact_rate * (0.5 + intensity)
    total_contacts = int(duration * contacts_per_second)
    
    for _ in range(total_contacts):
        # Random timing
        contact_time = random.uniform(0, duration)
        contact_pos = int(contact_time * SAMPLE_RATE)
        
        if contact_type == "soft":
            # Soft impact model
            impact_duration = 0.1 + random.uniform(0, 0.1)
            impact_samples = int(impact_duration * SAMPLE_RATE)
            
            if contact_pos + impact_samples < samples:
                # Generate impact using damped oscillation
                t = np.linspace(0, impact_duration, impact_samples, False)
                
                # Frequency based on contact intensity
                freq = 80 + (intensity * 40) + random.uniform(-10, 10)
                
                # Damped oscillation
                damping = 3 + (intensity * 2)
                impact = np.exp(-damping * t) * np.sin(2 * np.pi * freq * t)
                
                # Add some noise for texture
                noise = np.random.normal(0, 0.1, impact_samples)
                impact += 0.3 * noise
                
                # Scale by intensity
                impact *= 0.08 * intensity
                
                audio[contact_pos:contact_pos + impact_samples] += impact
        
        elif contact_type == "friction":
            # Friction model
            friction_duration = 0.2 + random.uniform(0, 0.3)
            friction_samples = int(friction_duration * SAMPLE_RATE)
            
            if contact_pos + friction_samples < samples:
                # Generate filtered noise for friction
                noise = np.random.normal(0, 1, friction_samples)
                
                # Apply frequency shaping
                freq_center = 1000 + (intensity * 2000)
                b, a = signal.butter(4, [freq_center - 500, freq_center + 500], btype='band', fs=SAMPLE_RATE)
                friction = signal.lfilter(b, a, noise)
                
                # Apply envelope
                envelope = np.exp(-3 * np.linspace(0, 1, friction_samples))
                friction *= envelope
                
                # Scale
                friction *= 0.06 * intensity
                
                audio[contact_pos:contact_pos + friction_samples] += friction
    
    return audio

def generate_breath_dynamics(duration, breath_rate=0.3, intensity=0.5):
    """Generate realistic breathing patterns with dynamics"""
    samples = int(duration * SAMPLE_RATE)
    audio = np.zeros(samples)
    
    # Breath cycle timing
    breaths_per_second = breath_rate * (0.8 + intensity * 0.4)
    breath_interval = 1.0 / breaths_per_second
    
    current_time = 0
    while current_time < duration:
        # Breath cycle duration with variation
        cycle_duration = breath_interval + random.uniform(-0.3, 0.5)
        
        # Inhale phase
        inhale_duration = cycle_duration * (0.4 + random.uniform(-0.1, 0.1))
        inhale_samples = int(inhale_duration * SAMPLE_RATE)
        inhale_pos = int(current_time * SAMPLE_RATE)
        
        if inhale_pos + inhale_samples < samples:
            # Generate inhale sound
            t = np.linspace(0, inhale_duration, inhale_samples, False)
            
            # Base frequency for breath
            base_freq = 40 + (intensity * 30)
            
            # Create breath sound with turbulence
            breath = np.sin(2 * np.pi * base_freq * t)
            
            # Add turbulent noise
            turbulence = np.random.normal(0, 0.5, inhale_samples)
            turbulence = signal.lfilter(*signal.butter(2, 200, fs=SAMPLE_RATE), turbulence)
            
            inhale_sound = 0.7 * breath + 0.3 * turbulence
            
            # Apply inhale envelope
            inhale_envelope = np.power(np.linspace(0, 1, inhale_samples), 0.5)
            inhale_sound *= inhale_envelope
            
            # Scale
            inhale_sound *= 0.04 * intensity
            
            audio[inhale_pos:inhale_pos + inhale_samples] += inhale_sound
        
        # Pause
        pause_duration = cycle_duration * 0.2
        
        # Exhale phase
        exhale_start = current_time + inhale_duration + pause_duration
        exhale_duration = cycle_duration * (0.4 + random.uniform(-0.1, 0.1))
        exhale_samples = int(exhale_duration * SAMPLE_RATE)
        exhale_pos = int(exhale_start * SAMPLE_RATE)
        
        if exhale_pos + exhale_samples < samples:
            # Generate exhale sound
            t = np.linspace(0, exhale_duration, exhale_samples, False)
            
            # Lower frequency for exhale
            exhale_freq = base_freq * 0.7
            
            # Create exhale with different character
            exhale = np.sin(2 * np.pi * exhale_freq * t)
            
            # Add soft noise
            soft_noise = np.random.normal(0, 0.3, exhale_samples)
            soft_noise = signal.lfilter(*signal.butter(2, 150, fs=SAMPLE_RATE), soft_noise)
            
            exhale_sound = 0.6 * exhale + 0.4 * soft_noise
            
            # Apply exhale envelope (reverse of inhale)
            exhale_envelope = np.power(np.linspace(1, 0, exhale_samples), 0.7)
            exhale_sound *= exhale_envelope
            
            # Scale
            exhale_sound *= 0.03 * intensity
            
            audio[exhale_pos:exhale_pos + exhale_samples] += exhale_sound
        
        current_time += cycle_duration
    
    return audio

def generate_enhanced_ambient_texture(duration, scene_type="intimate", intensity=0.5):
    """Generate enhanced ambient texture using advanced synthesis"""
    
    if scene_type.lower() in ["intimate", "sensual", "romantic"]:
        # Layer 1: Formant-based vocals
        vocals = generate_formant_vocal(duration, intensity)
        
        # Layer 2: Breath dynamics
        breathing = generate_breath_dynamics(duration, 0.25 + intensity * 0.15, intensity)
        
        # Layer 3: Soft contact physics
        contacts = generate_contact_physics(duration, 1.5 + intensity, intensity, "soft")
        
        # Layer 4: Granular texture for organic feel
        texture = generate_granular_texture(duration, 0.08, 0.6, intensity * 0.7)
        
        # Layer 5: Friction elements
        friction = generate_contact_physics(duration, 0.8 + intensity * 0.5, intensity * 0.8, "friction")
        
        # Combine layers with appropriate levels
        ambient = (0.4 * vocals + 
                  0.2 * breathing + 
                  0.25 * contacts + 
                  0.1 * texture + 
                  0.15 * friction)
        
    elif scene_type.lower() in ["dynamic", "energetic", "active"]:
        # More intense layering
        vocals = generate_formant_vocal(duration, intensity * 1.3)
        breathing = generate_breath_dynamics(duration, 0.4 + intensity * 0.2, intensity * 1.2)
        contacts = generate_contact_physics(duration, 2.5 + intensity * 1.5, intensity, "soft")
        friction = generate_contact_physics(duration, 1.5 + intensity, intensity, "friction")
        texture = generate_granular_texture(duration, 0.06, 0.8, intensity)
        
        ambient = (0.45 * vocals + 
                  0.25 * breathing + 
                  0.3 * contacts + 
                  0.2 * friction + 
                  0.15 * texture)
        
    else:
        # Minimal ambient
        breathing = generate_breath_dynamics(duration, 0.2, intensity * 0.7)
        texture = generate_granular_texture(duration, 0.1, 0.4, intensity * 0.5)
        ambient = 0.6 * breathing + 0.4 * texture
    
    # Final processing
    if np.max(np.abs(ambient)) > 0:
        # Normalize but preserve dynamics
        peak = np.max(np.abs(ambient))
        ambient = ambient / peak * 0.8
        
        # Apply subtle compression
        threshold = 0.5
        ratio = 3.0
        above_threshold = np.abs(ambient) > threshold
        ambient[above_threshold] = np.sign(ambient[above_threshold]) * (
            threshold + (np.abs(ambient[above_threshold]) - threshold) / ratio
        )
    
    return ambient

def analyze_clip_for_enhanced_audio(clip_metadata):
    """Enhanced analysis for more sophisticated audio generation"""
    start_data = clip_metadata.get('start', {})
    end_data = clip_metadata.get('end', {})
    
    # Base intensity analysis
    intensity = 0.4  # Slightly higher base
    
    action_words = (start_data.get('action', '') + ' ' + end_data.get('action', '')).lower()
    motion_words = (start_data.get('motion', '') + ' ' + end_data.get('motion', '')).lower()
    subject_words = (start_data.get('subject', '') + ' ' + end_data.get('subject', '')).lower()
    
    # Enhanced intensity mapping
    very_high_terms = ['intense', 'vigorous', 'rapid', 'hard', 'deep', 'passionate']
    high_intensity_terms = ['active', 'dynamic', 'energetic', 'fast', 'strong']
    medium_intensity_terms = ['moderate', 'steady', 'rhythmic', 'continuous', 'regular']
    low_intensity_terms = ['slow', 'gentle', 'soft', 'calm', 'still', 'tender']
    
    combined_text = action_words + ' ' + motion_words + ' ' + subject_words
    
    if any(term in combined_text for term in very_high_terms):
        intensity = 0.8 + random.uniform(0, 0.2)
    elif any(term in combined_text for term in high_intensity_terms):
        intensity = 0.6 + random.uniform(-0.1, 0.2)
    elif any(term in combined_text for term in medium_intensity_terms):
        intensity = 0.5 + random.uniform(-0.1, 0.1)
    elif any(term in combined_text for term in low_intensity_terms):
        intensity = 0.3 + random.uniform(-0.1, 0.1)
    
    # Scene type analysis
    scene_type = start_data.get('scene_type', 'intimate')
    
    # Action-specific modifications
    if 'licking' in action_words or 'sucking' in action_words:
        intensity *= 1.2  # Boost for specific actions
    
    return {
        'intensity': min(1.0, intensity),
        'scene_type': scene_type,
        'action_context': action_words,
        'motion_context': motion_words
    }

def create_enhanced_audio_for_manifest(manifest_path, out_dir):
    """Create enhanced procedural audio using advanced synthesis"""
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest_data = json.load(f)
    
    items = manifest_data.get("items", [])
    if not items:
        die("No items in manifest")
    
    print(f"Generating enhanced procedural audio for {len(items)} clips...")
    print("Using: Formant synthesis, granular synthesis, physics modeling")
    
    # Load metadata for enhanced analysis
    meta_dir = Path("E:/n8n_docker_strick/data/meta")
    clip_audio_data = []
    
    for item in items:
        base_name = item.get('base', Path(item.get('path', '')).stem)
        meta_file = meta_dir / f"{base_name}.json"
        
        if meta_file.exists():
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
            audio_params = analyze_clip_for_enhanced_audio(meta_data)
        else:
            audio_params = {
                'intensity': 0.5,
                'scene_type': 'intimate',
                'action_context': '',
                'motion_context': ''
            }
        
        clip_duration = item.get('clean_duration', item.get('t1', 5.0) - item.get('t0', 0.0))
        
        print(f"  {base_name}: {clip_duration:.1f}s, intensity={audio_params['intensity']:.2f}, type={audio_params['scene_type']}")
        
        clip_audio_data.append({
            'duration': clip_duration,
            'params': audio_params
        })
    
    # Generate enhanced audio for each clip
    audio_segments = []
    total_duration = 0
    
    print("\nGenerating audio segments...")
    for i, clip_data in enumerate(clip_audio_data):
        duration = clip_data['duration']
        params = clip_data['params']
        
        print(f"  Processing segment {i+1}/{len(clip_audio_data)}: {duration:.1f}s")
        
        # Generate enhanced ambient audio
        clip_audio = generate_enhanced_ambient_texture(
            duration, 
            params['scene_type'], 
            params['intensity']
        )
        
        audio_segments.append(clip_audio)
        total_duration += duration
    
    # Concatenate all audio segments
    print("Combining audio segments...")
    full_audio = np.concatenate(audio_segments)
    
    # Apply overall fade in/out
    fade_samples = int(1.0 * SAMPLE_RATE)  # 1 second fade
    if len(full_audio) > 2 * fade_samples:
        fade_in = np.linspace(0, 1, fade_samples)
        full_audio[:fade_samples] *= fade_in
        
        fade_out = np.linspace(1, 0, fade_samples)
        full_audio[-fade_samples:] *= fade_out
    
    # Convert to 16-bit integer
    audio_int16 = (full_audio * 32767).astype(np.int16)
    
    # Save enhanced audio file
    audio_output = out_dir / "enhanced_audio.wav"
    write(str(audio_output), SAMPLE_RATE, audio_int16)
    
    print(f"\nGenerated enhanced audio track:")
    print(f"  Duration: {total_duration:.1f}s")
    print(f"  Output: {audio_output}")
    print(f"  Synthesis: Formant + Granular + Physics")
    print(f"  Sample rate: {SAMPLE_RATE} Hz")
    
    return audio_output

def combine_video_with_audio(video_path, audio_path, output_path):
    """Combine video with generated audio using FFmpeg"""
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output_path)
    ]
    
    print(f"Combining video with enhanced audio...")
    
    proc = subprocess.run(cmd, text=True, capture_output=True)
    
    if proc.returncode != 0:
        print("FFmpeg error:")
        print(proc.stderr[-1000:])
        die("Failed to combine video and audio", proc.returncode)
    
    print(f"Created final video with enhanced audio: {output_path}")

def main():
    if len(sys.argv) < 2:
        die(f"Usage: {sys.argv[0]} <OUT_DIR>")
    
    out_dir = Path(sys.argv[1]).resolve()
    
    # Look for video files
    video_files = [
        out_dir / "combined_smooth_loops.mp4",
        out_dir / "combined_video_only.mp4",
        out_dir / "combined.mp4"
    ]
    
    video_file = None
    manifest_file = None
    
    # Find the best video and manifest pair
    if (out_dir / "smart_manifest_loop_trimmed.json").exists():
        manifest_file = out_dir / "smart_manifest_loop_trimmed.json"
        video_file = out_dir / "combined_smooth_loops.mp4"
    elif (out_dir / "smart_manifest.json").exists():
        manifest_file = out_dir / "smart_manifest.json"
        for vf in video_files:
            if vf.exists():
                video_file = vf
                break
    
    if not manifest_file or not manifest_file.exists():
        die("No manifest file found")
    
    if not video_file or not video_file.exists():
        die("No video file found")
    
    print("Enhanced Procedural Audio Generator")
    print("=" * 45)
    print(f"Video: {video_file.name}")
    print(f"Manifest: {manifest_file.name}")
    
    # Generate enhanced audio
    audio_file = create_enhanced_audio_for_manifest(manifest_file, out_dir)
    
    # Combine with video
    final_output = out_dir / f"{video_file.stem}_enhanced_audio.mp4"
    combine_video_with_audio(video_file, audio_file, final_output)
    
    print(f"\nComplete! Enhanced audio video: {final_output}")

if __name__ == "__main__":
    main()
