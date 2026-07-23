import pandas as pd
import numpy as np
from midiutil import MIDIFile
import os
import subprocess
import urllib.request
import ssl

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
    
    x_min, x_max = df[freq_col].min(), df[freq_col].max()
    
    midi = MIDIFile(5)
    TRACK_SANTOOR, TRACK_BANSURI, TRACK_SITAR, TRACK_TABLA, TRACK_TANPURA = range(5)
    CH_SANTOOR, CH_BANSURI, CH_SITAR, CH_TABLA, CH_TANPURA = 0, 1, 2, 9, 3
    
    midi.addProgramChange(TRACK_SANTOOR, CH_SANTOOR, 0, int(lead_inst))
    midi.addProgramChange(TRACK_BANSURI, CH_BANSURI, 0, int(echo_inst))
    midi.addProgramChange(TRACK_SITAR, CH_SITAR, 0, int(accent_inst))
    midi.addProgramChange(TRACK_TANPURA, CH_TANPURA, 0, 105)
    
    time = 0.0
    prev_region = None
    note_timeline = []
    
    for i, row in df.iterrows():
        region = str(row[struct_col])
        
        freq = scale_log_exp(float(row[freq_col]), x_min, x_max, freq_min, freq_max)
        
        if region != prev_region:
            raw_tempo = base_tempo_map.get(region, 60)
            tempo = int(raw_tempo * tempo_multiplier)
            midi.addTempo(TRACK_SANTOOR, time, tempo)
            prev_region = region
            
        midi_note = int(69 + 12 * np.log2(max(freq, 20.0) / 440))
        midi_note, svara_name = quantize_to_raag(midi_note, root_note, raag_name)
        
        duration = float(np.random.choice([0.5, 0.75, 1.0]))
        volume = int(np.random.randint(75, 95))
        
        # Lead Instrument
        midi.addNote(TRACK_SANTOOR, CH_SANTOOR, midi_note, time, duration, volume)
        
        # Echo Layer (delayed + softer)
        midi.addNote(TRACK_BANSURI, CH_BANSURI, max(midi_note - 12, 24), time + 0.5, duration, max(volume - 20, 30))
        
        # Accent Instrument on strong beats
        if i % 8 == 0:
            midi.addNote(TRACK_SITAR, CH_SITAR, max(midi_note - 5, 24), time, 1.2, 65)
            
        # Tabla rhythm (Teentaal structure)
        if enable_tabla:
            beat = i % 16
            if beat in [0, 8]:
                midi.addNote(TRACK_TABLA, CH_TABLA, 35, time, 0.4, 90) # Bass (Dha)
            elif beat in [4, 12]:
                midi.addNote(TRACK_TABLA, CH_TABLA, 38, time, 0.4, 80) # Snare (Tin)
            elif beat in [2, 6, 10, 14]:
                midi.addNote(TRACK_TABLA, CH_TABLA, 39, time, 0.2, 70) # High (Na)
                
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
            
        time += duration
        
    # Add Tanpura drone (Sa-Pa-Sa) matching the exact melody duration plus a 3-second tail
    if enable_drone:
        for t in np.arange(0, time + 3.0, 2.0):
            for n in [root_note - 12, root_note - 7, root_note]:
                midi.addNote(TRACK_TANPURA, CH_TANPURA, n, t, 2, 45)
        
    with open(output_mid_path, "wb") as f:
        midi.writeFile(f)
        
    print(f"Full Indian classical sonification complete: {output_mid_path}")
    
    if output_wav_path:
        sf2_path = "TimGM6mb.sf2"
        if not os.path.exists(sf2_path):
            print("Downloading SoundFont...")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen("https://github.com/craffel/pretty-midi/raw/main/pretty_midi/TimGM6mb.sf2", context=ctx) as u, open(sf2_path, 'wb') as f:
                f.write(u.read())
            
        print("Converting to WAV using fluidsynth...")
        subprocess.run(["fluidsynth", "-ni", "-F", output_wav_path, "-r", "44100", "-q", sf2_path, output_mid_path])
        print(f"Done! Saved audio as: {output_wav_path}")

    return {
        "total_duration": round(float(time), 2),
        "total_residues": len(note_timeline),
        "timeline": note_timeline
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert BMRB chemical shift data to Indian Classical Music")
    parser.add_argument("input_csv", help="Input CSV file with Final_Freq and Secondary Structure columns")
    parser.add_argument("output_mid", help="Output MIDI file path")
    parser.add_argument("--wav", dest="output_wav", help="Optional Output WAV file path (requires fluidsynth)", default=None)
    
    args = parser.parse_args()
    sonify_bmrb(args.input_csv, args.output_mid, args.output_wav)
