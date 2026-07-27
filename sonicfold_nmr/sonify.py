import pandas as pd
import numpy as np
from midiutil import MIDIFile
import os
import subprocess
import urllib.request
import ssl
import math
import hashlib
import scipy.io.wavfile as wav

RAAG_SCALES = {
    "Yaman": {
        "intervals": [0, 2, 4, 6, 7, 9, 11],
        "names": ["Sa", "Re", "Ga", "Ma#", "Pa", "Dha", "Ni"]
    },
    "Bhairav": {
        "intervals": [0, 1, 4, 5, 7, 8, 11],
        "names": ["Sa", "re", "Ga", "Ma", "Pa", "dha", "Ni"]
    },
    "Bhupali": {
        "intervals": [0, 2, 4, 7, 9],
        "names": ["Sa", "Re", "Ga", "Pa", "Dha"]
    },
    "Kafi": {
        "intervals": [0, 2, 3, 5, 7, 9, 10],
        "names": ["Sa", "Re", "ga", "Ma", "Pa", "Dha", "ni"]
    },
    "Malkauns": {
        "intervals": [0, 3, 5, 8, 10],
        "names": ["Sa", "ga", "Ma", "dha", "ni"]
    }
}

def scale_log_exp(x, x_min, x_max, freq_min=240, freq_max=480):
    if x_max == x_min:
        return (freq_min + freq_max) / 2
    norm = (x - x_min) / (x_max - x_min)
    scaled = (np.exp(norm) - 1) / (np.e - 1)
    return freq_min + scaled * (freq_max - freq_min)

def quantize_to_raag(note, root_note=60, raag_name="Yaman"):
    raag_data = RAAG_SCALES.get(raag_name, RAAG_SCALES["Yaman"])
    scale = raag_data["intervals"]
    names = raag_data["names"]
    
    degree = (note - root_note) % 12
    closest_idx = min(range(len(scale)), key=lambda idx: abs(scale[idx] - degree))
    closest = scale[closest_idx]
    svara = names[closest_idx]
    
    quantized_note = note - degree + closest
    return quantized_note, svara

def get_time_in_seconds(target_beat, tempo_changes):
    sec = 0.0
    curr_b = 0.0
    curr_tempo = 60.0
    for b, tempo in tempo_changes:
        if target_beat <= b:
            break
        sec += (b - curr_b) / (curr_tempo / 60.0)
        curr_b = b
        curr_tempo = tempo
    
    if target_beat > curr_b:
        sec += (target_beat - curr_b) / (curr_tempo / 60.0)
    return sec

def sonify_bmrb(
    csv_path,
    output_mid_path,
    output_wav_path=None,
    raag_name="Yaman",
    root_note=60,
    tempo_multiplier=1.0,
    lead_inst=107,
    echo_inst=74,
    accent_inst=104,
    enable_drone=True,
    enable_tabla=True,
    freq_min=240,
    freq_max=480
):
    df = pd.read_csv(csv_path)
    
    # Identify frequency column
    freq_col = None
    for col in ['Final_Freq', 'Effective', 'final_freq', 'frequency', 'Freq']:
        if col in df.columns:
            freq_col = col
            break
    if freq_col is None:
        # Fallback to the last numeric column
        freq_col = df.select_dtypes(include=[np.number]).columns[-1]
        
    # Identify secondary structure column
    struct_col = None
    for col in ['Secondary Structure', 'secondary_structure', 'Secondary_Structure', 'Structure', 'ss']:
        if col in df.columns:
            struct_col = col
            break
    if struct_col is None:
        df['Secondary Structure'] = 'Random coil'
        struct_col = 'Secondary Structure'
        
    # Ensure columns exist and drop NAs
    df = df.dropna(subset=[freq_col, struct_col]).copy()
    df.reset_index(drop=True, inplace=True)
    
    # Base tempo mapping based on secondary structure multiplied by tempo_multiplier
    base_tempo_map = {
        'Alpha helix': 60,
        'Beta sheet': 80,
        'Random coil': 50,
        'H': 60,
        'B': 80,
        'R': 50,
        'C': 50
    }
    
    base_cutoff_map = {
        'Alpha helix': 75,
        'H': 75,
        'Beta sheet': 110,
        'B': 110,
        'Random coil': 40,
        'R': 40,
        'C': 40
    }
    
    base_duration_map = {
        'Alpha helix': 1.0,
        'H': 1.0,
        'Beta sheet': 0.5,
        'B': 0.5,
        'Random coil': 0.75,
        'R': 0.75,
        'C': 0.75
    }
    
    x_min, x_max = df[freq_col].min(), df[freq_col].max()
    
    midis = {
        'santoor': MIDIFile(1),
        'bansuri': MIDIFile(1),
        'sitar': MIDIFile(1),
        'tabla': MIDIFile(1),
        'tanpura': MIDIFile(1)
    }
    
    midis['santoor'].addProgramChange(0, 0, 0, int(lead_inst))
    midis['bansuri'].addProgramChange(0, 0, 0, int(echo_inst))
    midis['sitar'].addProgramChange(0, 0, 0, int(accent_inst))
    midis['tanpura'].addProgramChange(0, 0, 0, 105)
    
    time = 0.0
    prev_region = None
    note_timeline = []
    tempo_changes = []
    tension_timeline = []
    
    # Calculate deviation score for data-driven volume
    aa_col = 'chem_comp_ID' if 'chem_comp_ID' in df.columns else 'res_name' if 'res_name' in df.columns else None
    if aa_col:
        aa_means = df.groupby(aa_col)[freq_col].transform('mean')
        df['deviation'] = abs(df[freq_col] - aa_means)
    else:
        df['deviation'] = abs(df[freq_col] - df[freq_col].mean())
        
    max_dev = df['deviation'].max()
    if max_dev == 0:
        max_dev = 1.0
        
    # Calculate structural tension (rolling variance of deviation)
    df['tension'] = df['deviation'].rolling(window=5, center=True).var().fillna(0)
    max_tension = df['tension'].max()
    if max_tension == 0:
        max_tension = 1.0
    df['tension_norm'] = df['tension'] / max_tension
    
    # Deterministic seeding based on amino acid sequence to guarantee reproducible output
    aa_sequence = "".join([str(row.get("chem_comp_ID", row.get("res_name", "ALA"))) for _, row in df.iterrows()])
    seed_val = int(hashlib.sha256(aa_sequence.encode('utf-8')).hexdigest(), 16) % (2**32)
    np.random.seed(seed_val)
    
    for i, row in df.iterrows():
        region = str(row[struct_col])
        
        freq = scale_log_exp(float(row[freq_col]), x_min, x_max, freq_min, freq_max)
        
        if region != prev_region:
            raw_tempo = base_tempo_map.get(region, 60)
            tempo = int(raw_tempo * tempo_multiplier)
            for m in midis.values():
                m.addTempo(0, time, tempo)
            tempo_changes.append((time, tempo))
            prev_region = region
            
        midi_note = int(69 + 12 * np.log2(max(freq, 20.0) / 440))
        midi_note, svara_name = quantize_to_raag(midi_note, root_note, raag_name)
        
        duration = float(base_duration_map.get(region, 0.75))
        
        # Volume mapped to normalized deviation (75 to 95)
        norm_dev = float(row['deviation']) / max_dev
        volume = int(75 + (norm_dev * 20))
        
        # Add filter cutoff with sine wave wobble
        base_cutoff = base_cutoff_map.get(region, 40)
        wobble_amplitude = 15
        wobble_freq = 0.25 # Hz (Slow sweeping LFO)
        
        # Calculate cutoff with wobble based on note start time
        wobble_val = wobble_amplitude * math.sin(2 * math.pi * wobble_freq * time)
        target_cutoff = int(max(0, min(127, base_cutoff + wobble_val)))
        
        # Insert controller events slightly before note-on (e.g. 0.01 beats before)
        cc_time = max(0, time - 0.01)
        
        midis['santoor'].addControllerEvent(0, 0, cc_time, 74, target_cutoff)
        midis['santoor'].addControllerEvent(0, 0, cc_time, 71, 45)
        
        midis['bansuri'].addControllerEvent(0, 0, cc_time, 74, target_cutoff)
        midis['bansuri'].addControllerEvent(0, 0, cc_time, 71, 45)
        
        midis['sitar'].addControllerEvent(0, 0, cc_time, 74, target_cutoff)
        midis['sitar'].addControllerEvent(0, 0, cc_time, 71, 45)
        
        # Lead Instrument
        midis['santoor'].addNote(0, 0, midi_note, time, duration, volume)
        
        # Echo Layer (delayed + softer)
        midis['bansuri'].addNote(0, 0, max(midi_note - 12, 24), time + 0.5, duration, max(volume - 20, 30))
        
        # Accent Instrument on strong beats
        if i % 8 == 0:
            midis['sitar'].addNote(0, 0, max(midi_note - 5, 24), time, 1.2, 65)
            
        # Tabla rhythm (Teentaal structure)
        if enable_tabla:
            beat = i % 16
            if beat in [0, 8]:
                midis['tabla'].addNote(0, 9, 35, time, 0.4, 90) # Bass (Dha)
            elif beat in [4, 12]:
                midis['tabla'].addNote(0, 9, 38, time, 0.4, 80) # Snare (Tin)
            elif beat in [2, 6, 10, 14]:
                midis['tabla'].addNote(0, 9, 39, time, 0.2, 70) # High (Na)
                
        # Record event for frontend synchronization
        seq_num = row.get("sequence", i + 1)
        amino_acid = row.get("chem_comp_ID", row.get("res_name", "ALA"))
        note_timeline.append({
            "index": int(i),
            "sequence": int(seq_num) if pd.notnull(seq_num) else int(i + 1),
            "amino_acid": str(amino_acid),
            "secondary_structure": region,
            "final_freq": round(float(row[freq_col]), 2),
            "scaled_freq": round(float(freq), 2),
            "midi_note": int(midi_note),
            "svara": svara_name,
            "time": round(float(time), 2),
            "duration": round(float(duration), 2)
        })
        
        tension_timeline.append({
            'beat': time,
            'duration_beats': duration,
            'tension': float(row['tension_norm'])
        })
            
        time += duration
        
    # Add Tanpura drone (Sa-Pa-Sa) matching the exact melody duration plus a 3-second tail
    if enable_drone:
        for t in np.arange(0, time + 3.0, 2.0):
            for n in [root_note - 12, root_note - 7, root_note]:
                midis['tanpura'].addNote(0, 0, n, t, 2, 45)
                
    # Save midis
    mid_dir = os.path.dirname(output_mid_path)
    if not mid_dir:
        mid_dir = "."
    base_name = os.path.basename(output_mid_path).replace(".mid", "")
    
    stems_dir = os.path.join(mid_dir, f"{base_name}_stems")
    os.makedirs(stems_dir, exist_ok=True)
    
    for name, m in midis.items():
        path = os.path.join(stems_dir, f"{name}.mid")
        with open(path, "wb") as f:
            m.writeFile(f)
            
    # Save the santoor track for the main output_mid_path to avoid breaking things
    with open(output_mid_path, "wb") as f:
        midis['santoor'].writeFile(f)
        
    print(f"Full Indian classical sonification complete. Stems saved to {stems_dir}")
    
    if output_wav_path:
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        sf2_path = os.path.join(base_dir, "TimGM6mb.sf2")
        
        if not os.path.exists(sf2_path):
            print("Downloading SoundFont...")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen("https://github.com/craffel/pretty-midi/raw/main/pretty_midi/TimGM6mb.sf2", context=ctx) as u, open(sf2_path, 'wb') as f:
                f.write(u.read())
            
        print("Rendering stems to WAV...")
        wav_paths = {}
        fluidsynth_ok = True
        
        # Determine the correct fluidsynth command based on OS and bundling
        if os.name == 'nt' and getattr(sys, 'frozen', False):
            # Bundled in PyInstaller on Windows
            fluidsynth_cmd = os.path.join(base_dir, "fluidsynth", "bin", "fluidsynth.exe")
        else:
            # Mac, Linux (Web), or non-frozen Windows
            fluidsynth_cmd = "fluidsynth"

        for name in midis.keys():
            mid_path = os.path.join(stems_dir, f"{name}.mid")
            wav_path = os.path.join(stems_dir, f"{name}.wav")
            try:
                subprocess.run([fluidsynth_cmd, "-ni", "-F", wav_path, "-r", "44100", "-q", sf2_path, mid_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                wav_paths[name] = wav_path
            except FileNotFoundError:
                print(f"Warning: fluidsynth not found. Cannot generate WAV for {name}.")
                fluidsynth_ok = False
                break
                
        if fluidsynth_ok:
            print("Applying tension-scaled distortion and mixing...")
            
            # Convert tension_timeline (beats) to seconds
            tension_sec = []
            for t in tension_timeline:
                start_sec = get_time_in_seconds(t['beat'], tempo_changes)
                end_sec = get_time_in_seconds(t['beat'] + t['duration_beats'], tempo_changes)
                tension_sec.append({'start': start_sec, 'end': end_sec, 'tension': t['tension']})
                
            # Load WAVs
            audio_data = {}
            target_len = 0
            sr = 44100
            for name, path in wav_paths.items():
                sr_read, data = wav.read(path)
                audio_data[name] = data
                if len(data) > target_len:
                    target_len = len(data)
                    
            # Pad all arrays to target_len
            for name in audio_data:
                data = audio_data[name]
                if len(data) < target_len:
                    pad_width = target_len - len(data)
                    if data.ndim == 2:
                        data = np.pad(data, ((0, pad_width), (0,0)), mode='constant')
                    else:
                        data = np.pad(data, (0, pad_width), mode='constant')
                    audio_data[name] = data
                    
            # Build gain envelope
            gain_envelope = np.ones(target_len, dtype=np.float32)
            for t in tension_sec:
                start_samp = min(target_len, int(t['start'] * sr))
                end_samp = min(target_len, int(t['end'] * sr))
                gain_envelope[start_samp:end_samp] = 1.0 + t['tension'] * 15.0 # up to 16x gain
                
            def apply_distortion(audio_arr):
                audio_f = audio_arr.astype(np.float32) / 32768.0
                
                if audio_f.ndim == 2:
                    g = gain_envelope[:, np.newaxis]
                else:
                    g = gain_envelope
                    
                dist = np.tanh(audio_f * g)
                return dist
                
            audio_data['sitar'] = apply_distortion(audio_data['sitar'])
            audio_data['tabla'] = apply_distortion(audio_data['tabla'])
            
            # Convert others to float
            for name in ['santoor', 'bansuri', 'tanpura']:
                audio_data[name] = audio_data[name].astype(np.float32) / 32768.0
                
            # Mix
            mixed = np.zeros_like(audio_data['santoor'], dtype=np.float32)
            for data in audio_data.values():
                mixed += data
                
            # Normalize
            max_val = np.max(np.abs(mixed))
            if max_val > 0:
                mixed = mixed / max_val * 0.95 
                
            # Write to final WAV
            mixed_int16 = (mixed * 32767.0).astype(np.int16)
            wav.write(output_wav_path, sr, mixed_int16)
            print(f"Done! Final mix saved to {output_wav_path}")
        else:
            print("Skipped WAV generation because fluidsynth is missing.")

    return {
        "total_duration": round(float(time), 2),
        "total_residues": len(note_timeline),
        "timeline": note_timeline
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert BMRB chemical shift data to Indian Classical Music")
    parser.add_argument("input_csv", help="Input CSV file with Final_Freq and Secondary Structure columns")
    parser.add_argument("output_mid", help="Output main MIDI file path")
    parser.add_argument("--wav", dest="output_wav", help="Optional Output WAV file path (requires fluidsynth)", default=None)
    
    args = parser.parse_args()
    sonify_bmrb(args.input_csv, args.output_mid, args.output_wav)

if __name__ == "__main__":
    main()
