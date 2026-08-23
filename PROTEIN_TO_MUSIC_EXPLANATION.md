# 🎵 From Proteins to Music — A Complete Explanation
### *BioNMR IITG · Cosmic Raga Molecular Sonification*

---

## Table of Contents

1. [What is a Protein?](#1-what-is-a-protein)
2. [What is NMR Spectroscopy?](#2-what-is-nmr-spectroscopy)
3. [What are Chemical Shifts?](#3-what-are-chemical-shifts)
4. [The BMRB and PDB Databases](#4-the-bmrb-and-pdb-databases)
5. [What Data Do We Start With?](#5-what-data-do-we-start-with)
6. [Step 1 — Frequency Scaling (Chemical Shift → Audio Hz)](#6-step-1--frequency-scaling)
7. [Step 2 — MIDI Note Mapping (Hz → Musical Note)](#7-step-2--midi-note-mapping)
8. [Step 3 — Quantization to an Indian Classical Raag](#8-step-3--quantization-to-a-raag)
9. [Step 4 — Secondary Structure → Tempo](#9-step-4--secondary-structure--tempo)
10. [Step 5 — Building the Multi-Layer MIDI Composition](#10-step-5--building-the-midi-composition)
11. [Step 6 — Rendering to Audio (MIDI → WAV)](#11-step-6--rendering-to-audio)
12. [The Full Pipeline at a Glance](#12-the-full-pipeline-at-a-glance)
13. [What Makes This Scientifically Meaningful?](#13-what-makes-this-scientifically-meaningful)
14. [Glossary](#14-glossary)

---

## 1. What is a Protein?

A **protein** is a long chain of small molecular building blocks called **amino acids**, linked
together like beads on a necklace. There are **20 standard amino acids**, each with a unique
chemical identity (e.g. Alanine `ALA`, Valine `VAL`, Lysine `LYS`, Tryptophan `TRP`, etc.).

The linear sequence of amino acids folds into a complex 3D shape, and this **3D shape determines
the protein's function** — whether it binds a drug, catalyzes a reaction, transmits a signal, or
builds a cell wall.

The 3D fold produces recurring structural patterns:
- **α-Helix (Alpha Helix)** — a right-handed spiral coil, like a spring
- **β-Sheet (Beta Sheet)** — flat strands running alongside each other
- **Random Coil** — flexible, less-ordered regions connecting the above

---

## 2. What is NMR Spectroscopy?

**Nuclear Magnetic Resonance (NMR) Spectroscopy** is a technique used to study the structure and
dynamics of proteins in **solution** (not crystals). It works by:

1. Placing the protein sample inside a powerful magnet.
2. Pulsing it with radio-frequency (RF) waves at precise frequencies.
3. The atomic nuclei in the protein (especially ¹H Hydrogen and ¹⁵N Nitrogen) absorb and re-emit
   these RF waves at frequencies that are **unique to their local chemical environment**.
4. Recording those emitted frequencies — this is the NMR spectrum.

Because every amino acid residue has a slightly different chemical environment depending on its
neighbours, its secondary structure, and the shape of the protein, **the frequency at which each
residue resonates is unique to that protein's structure**.

A common experiment is the **¹H–¹⁵N HSQC** (Heteronuclear Single Quantum Coherence), which
produces one peak (one spot on a 2D plot) **per amino acid residue** in the protein. It is called
a "protein fingerprint."

---

## 3. What are Chemical Shifts?

A **chemical shift** (measured in **ppm — parts per million**) is the precise NMR frequency of a
nucleus, expressed relative to a standard reference compound (TMS). It reflects the electron
density and bonding environment around the nucleus.

| Nucleus | Typical Chemical Shift Range | Information Encoded |
|---------|------------------------------|---------------------|
| ¹H (Hydrogen) | 6.5 – 10.5 ppm | H-bonds, secondary structure, folding |
| ¹⁵N (Nitrogen) | 105 – 135 ppm | Backbone amide environment |

In the HSQC experiment:
- The **X-axis** is the ¹H chemical shift of the amide hydrogen (NH)
- The **Y-axis** is the ¹⁵N chemical shift of the amide nitrogen

For our music pipeline, these ppm values are converted to **Hz (Hertz)** by multiplying by the
spectrometer frequency (750 MHz for ¹H, 75 MHz for ¹⁵N).

For example, from our dataset (`6188_simulated_hsqc_backbone_example_music.csv`):

```
sequence  chem_comp_ID  X_shift(ppm)  Y_shift(ppm)  H_Hz     N_Hz      Effective
1         VAL           7.82          119.41         5865.0   8955.75   7247.45
2         SER           9.40          120.06         7050.0   9004.50   7967.54
3         GLN           8.82          121.44         6615.0   9108.00   7762.05
```

- `H_Hz` = ¹H chemical shift × 750 MHz spectrometer frequency
- `N_Hz` = ¹⁵N chemical shift × 75 MHz
- `Effective` = geometric mean combining both dimensions into one number used for music

The Effective frequency formula:

```
Effective = sqrt(H_Hz × N_Hz)  [approximately, scaled by constants]
```

This gives one single number per residue that encodes its position in the 2D HSQC fingerprint.

---

## 4. The BMRB and PDB Databases

| Database | Full Name | What it Stores |
|----------|-----------|----------------|
| **BMRB** | Biological Magnetic Resonance Data Bank | NMR chemical shift data for proteins |
| **PDB** | Protein Data Bank | 3D atomic coordinates (X-ray, NMR, Cryo-EM) |

- **BMRB ID** (e.g. `6188`) → chemical shift table (the music data)
- **PDB ID** (e.g. `1ST7`) → 3D structure for WebGL visualisation

In our system the user enters a BMRB or PDB ID, the backend fetches the chemical shift data, and
the 3D viewer loads the PDB structure in the browser.

---

## 5. What Data Do We Start With?

For each protein residue, we have these columns after data loading:

| Column | Meaning | Example |
|--------|---------|---------|
| `sequence` | Residue position number | 1, 2, 3 … 85 |
| `chem_comp_ID` | Amino acid 3-letter code | `VAL`, `SER`, `GLN` |
| `Final_Freq` / `Effective` | Combined NMR frequency (Hz) | 7247, 7967, 7762 |
| `Secondary Structure` | Structural region of the residue | `Alpha helix`, `Beta sheet`, `Random coil` |

**One row = one amino acid residue = one musical note.**

The Yeast ACBP protein (BMRB 6188) has 85 residues, so the music has 85 notes.

---

## 6. Step 1 — Frequency Scaling (Chemical Shift → Audio Hz)

The NMR Effective frequencies range roughly from **6,500 to 8,800 Hz** — these are not audible
musical pitches. We must **scale** them down into the musically useful range of **240–480 Hz**.

We use a **log-exponential scaling** function from `sonify.py`:

```python
def scale_log_exp(x, x_min, x_max, freq_min=240, freq_max=480):
    norm = (x - x_min) / (x_max - x_min)        # Normalise to [0, 1]
    scaled = (np.exp(norm) - 1) / (np.e - 1)    # Apply exponential curve
    return freq_min + scaled * (freq_max - freq_min)
```

### Why exponential (not linear) scaling?

Human pitch perception is **logarithmic** — an octave is always a doubling of frequency. Using an
exponential transform ensures that smaller differences in chemical shift at the low end produce
larger perceptual pitch steps, preserving the **relative contrast** of the biological data.

| NMR Effective (Hz) | Scaled Musical Frequency |
|--------------------|--------------------------|
| Minimum (~6,500) | ~240 Hz — low register |
| Mid-range (~7,500) | ~340 Hz — middle |
| Maximum (~8,800) | ~480 Hz — high register |

---

## 7. Step 2 — MIDI Note Mapping (Hz → Musical Note)

Standard digital music uses **MIDI note numbers** (integers 0–127):
- MIDI 60 = Middle C (C4) = 261.63 Hz
- MIDI 69 = A4 = 440 Hz (standard tuning reference)

We convert the scaled Hz to a MIDI note using the standard formula:

```
MIDI note = 69 + 12 × log₂(f / 440)
```

```python
midi_note = int(69 + 12 * np.log2(max(freq, 20.0) / 440))
```

Example mappings:
- 240 Hz → MIDI 59 (B3)
- 340 Hz → MIDI 65 (F4)
- 480 Hz → MIDI 72 (C5)

**At this stage each residue has a raw MIDI note directly encoding its NMR chemical shift.**

---

## 8. Step 3 — Quantization to a Raag

A raw MIDI note can land on any of the 12 chromatic notes of Western music. We want to constrain
each note to an **Indian Classical Raag** without disturbing the scientific ordering.

### What is a Raag?

A **Raag** (राग) is a melodic scale in Indian Classical Music specifying:
- A **set of permitted notes (svaras)** within an octave
- An emotional mood (rasa)

We implement five Raags defined by their semitone intervals from Sa (the root):

| Raag | Semitone Intervals | Svaras | Mood |
|------|--------------------|--------|------|
| **Yaman** | 0, 2, 4, 6, 7, 9, 11 | Sa Re Ga Ma# Pa Dha Ni | Serene evening |
| **Bhairav** | 0, 1, 4, 5, 7, 8, 11 | Sa re Ga Ma Pa dha Ni | Majestic morning |
| **Bhupali** | 0, 2, 4, 7, 9 | Sa Re Ga Pa Dha | Joyful (pentatonic) |
| **Kafi** | 0, 2, 3, 5, 7, 9, 10 | Sa Re ga Ma Pa Dha ni | Expressive |
| **Malkauns** | 0, 3, 5, 8, 10 | Sa ga Ma dha ni | Deep meditative night |

### How quantization works in code (`sonify.py`):

```python
def quantize_to_raag(note, root_note=60, raag_name="Yaman"):
    scale = RAAG_SCALES[raag_name]["intervals"]   # e.g. [0,2,4,6,7,9,11]
    degree = (note - root_note) % 12              # Semitone within octave

    # Find the nearest permitted note in the Raag
    closest_idx = min(range(len(scale)), key=lambda i: abs(scale[i] - degree))
    closest = scale[closest_idx]
    svara = names[closest_idx]                    # e.g. "Ga", "Pa", "Ma#"

    quantized_note = note - degree + closest      # Snap to scale
    return quantized_note, svara
```

**Scientific integrity is fully preserved**: a residue with a larger Effective frequency always
produces a higher pitch. Quantization only rounds to the nearest allowed note — it never
re-orders the data.

### Worked Example (Raag Yaman, Sa = C4 = MIDI 60)

| Residue | AA  | Effective Hz | Scaled Hz | Raw MIDI | Semitone | Nearest Yaman | Svara  |
|---------|-----|-------------|-----------|----------|----------|---------------|--------|
| 1       | VAL | 7247        | 318 Hz    | 64       | 4 (E)    | 4 (Ga)        | **Ga** |
| 2       | SER | 7968        | 391 Hz    | 67       | 7 (G)    | 7 (Pa)        | **Pa** |
| 3       | GLN | 7762        | 365 Hz    | 66       | 6 (F#)   | 6 (Ma#)       | **Ma#**|

---

## 9. Step 4 — Secondary Structure → Tempo

The **secondary structure** of each residue determines the **tempo** (BPM) of the music in that
region of the protein:

| Secondary Structure | Base Tempo (BPM) | Musical Character |
|---------------------|-----------------|-------------------|
| **α-Helix** | 60 BPM | Moderate, flowing |
| **β-Sheet** | 80 BPM | Brisk, decisive |
| **Random Coil** | 50 BPM | Slow, contemplative |

```python
base_tempo_map = {
    'Alpha helix': 60,
    'Beta sheet':  80,
    'Random coil': 50,
}
tempo = int(base_tempo_map[region] * tempo_multiplier)
midi.addTempo(TRACK_SANTOOR, time, tempo)
```

The tempo updates automatically at every secondary structure transition. This means **the rhythm
of the music encodes the 3D topology of the protein**.

---

## 10. Step 5 — Building the Multi-Layer MIDI Composition

We construct a **5-Track MIDI file**:

```
Track 0  (CH 0 ) — SANTOOR / Lead   — Main melody: one note per residue
Track 1  (CH 1 ) — BANSURI / Echo   — Delayed octave echo of the melody
Track 2  (CH 2 ) — SITAR  / Accent  — Accent every 8th residue
Track 3  (CH 3 ) — TANPURA / Drone  — Continuous Sa–Pa harmonic drone
Track 4  (CH 9 ) — TABLA  / Rhythm  — Teentaal 16-beat drum cycle
```

### Track 0 — Lead Melody (Santoor)

One note per amino acid residue, pitched to its NMR chemical shift, snapped to the Raag.

```python
duration = float(np.random.choice([0.5, 0.75, 1.0]))   # Natural rhythmic variation
volume   = int(np.random.randint(75, 95))               # Dynamic expression
midi.addNote(TRACK_SANTOOR, CH_SANTOOR, midi_note, time, duration, volume)
```

### Track 1 — Echo Layer (Bansuri)

Same note one octave lower, delayed by 0.5 beats, at 70% volume — replicating natural resonance.

```python
midi.addNote(TRACK_BANSURI, CH_BANSURI, midi_note - 12, time + 0.5, duration, volume - 20)
```

### Track 2 — Structural Accent (Sitar)

Every 8th residue, a Sitar accent marks the sequence rhythm — like a bar line.

```python
if i % 8 == 0:
    midi.addNote(TRACK_SITAR, CH_SITAR, midi_note - 5, time, 1.2, 65)
```

### Track 3 — Tanpura Drone (Sa–Pa–Sa)

A continuous low drone on the root (Sa), fifth (Pa), and lower octave (Sa), providing the
tonal foundation throughout the entire piece.

```python
for t in np.arange(0, 240, 2):
    for n in [root_note - 12, root_note - 7, root_note]:   # Sa  Pa  Sa
        midi.addNote(TRACK_TANPURA, CH_TANPURA, n, t, 2, 45)
```

### Track 4 — Tabla Teentaal Rhythm

A 16-beat Teentaal cycle driven by the residue index:

| Beat (i % 16) | Note | Syllable | Volume |
|---------------|------|----------|--------|
| 0, 8 | MIDI 35 (Bass) | Dha | 90 |
| 4, 12 | MIDI 38 (Snare) | Tin | 80 |
| 2, 6, 10, 14 | MIDI 39 (Hi) | Na | 70 |

```python
beat = i % 16
if beat in [0, 8]:     midi.addNote(TRACK_TABLA, CH_TABLA, 35, time, 0.4, 90)
elif beat in [4, 12]:  midi.addNote(TRACK_TABLA, CH_TABLA, 38, time, 0.4, 80)
elif beat in [2,6,10,14]: midi.addNote(TRACK_TABLA, CH_TABLA, 39, time, 0.2, 70)
```

---

## 11. Step 6 — Rendering to Audio (MIDI → WAV)

The MIDI file is rendered to `.wav` using **FluidSynth** and the **TimGM6mb SoundFont**:

```bash
fluidsynth -ni -F music_output.wav -r 44100 TimGM6mb.sf2 music_output.mid
```

- **FluidSynth** — open-source software synthesizer
- **TimGM6mb.sf2** — SoundFont with sampled acoustic instruments (Santoor, Bansuri, Sitar, etc.)
- **44,100 Hz** sample rate — CD quality audio

The `.wav` is served to the browser for live playback, synchronized with the 3D molecular viewer
and the bottom amino acid ribbon strip.

---

## 12. The Full Pipeline at a Glance

```
PROTEIN
   │
   ▼
NMR EXPERIMENT (¹H–¹⁵N HSQC)
   │
   ▼
CHEMICAL SHIFTS per residue (ppm → Hz)
   │    H_Hz = ¹H_ppm × 750 MHz
   │    N_Hz = ¹⁵N_ppm × 75 MHz
   │    Effective = geometric_mean(H_Hz, N_Hz)
   ▼
LOG-EXPONENTIAL SCALING (Effective Hz → 130–1046 Hz)
   │
   ▼
MIDI NOTE NUMBER  [= 69 + 12 × log₂(f / 440)]
   │
   ▼
RAAG QUANTIZATION  (snap to nearest svara: Sa, Re, Ga, Ma, Pa, Dha, Ni)
   │
   │   ← Secondary Structure sets TEMPO (Helix=60, Sheet=80, Coil=50 BPM)
   ▼
5-TRACK MIDI FILE
   │  Track 0  Santoor melody (one note per residue)
   │  Track 1  Bansuri echo (octave below, delayed)
   │  Track 2  Sitar accent (every 8th residue)
   │  Track 3  Tanpura drone (Sa–Pa continuous)
   │  Track 4  Tabla Teentaal rhythm (16-beat cycle)
   ▼
FLUIDSYNTH + TimGM6mb SoundFont
   │
   ▼
WAV AUDIO FILE (44,100 Hz, CD quality)
   │
   ▼
BROWSER PLAYBACK
   │  3D molecular viewer — sphere ball glows per residue
   │  Bottom amino acid strip — card highlights in AA color
   └  Live HUD — shows current residue, svara, frequency
```

---

## 13. What Makes This Scientifically Meaningful?

### Scientific fidelity is preserved
The pitch ordering is a **direct monotonic mapping** of NMR chemical shifts. A residue with a
larger Effective frequency always produces a higher pitch. Raag quantization only rounds to the
nearest allowed note without shuffling or distorting the data.

### Secondary structure is aurally distinguishable
α-Helices at 60 BPM versus β-Sheets at 80 BPM means a listener can **hear the secondary
structure transitions** in real time. This is the core scientific communication value of
sonification.

### Each amino acid is uniquely identifiable
The 3D sphere glows in a **unique color per amino acid** (20 distinct vibrant colors grouped
biochemically — basic residues in blue, hydrophobic in green, aromatic in orange), mirrored in
the bottom ribbon strip and the live HUD badge.

### One note = one residue = one data point
There is no artistic interpolation. Every note in the composition maps **1-to-1 to a real amino
acid residue** with its measured NMR chemical shift.

---

## 14. Glossary

| Term | Meaning |
|------|---------|
| **Amino acid** | Basic building block of proteins; 20 standard types |
| **Residue** | One amino acid unit within a protein chain |
| **Chemical shift (ppm)** | NMR resonance frequency of a nucleus relative to a standard |
| **HSQC** | NMR experiment giving one peak per backbone NH group |
| **BMRB** | Biological Magnetic Resonance Data Bank |
| **PDB** | Protein Data Bank — 3D atomic coordinate database |
| **MIDI** | Musical Instrument Digital Interface — digital music protocol |
| **Raag** | Indian Classical melodic scale with emotional mood |
| **Svara** | A note in Indian Classical music (Sa Re Ga Ma Pa Dha Ni) |
| **Teentaal** | 16-beat rhythmic cycle in North Indian Classical Music |
| **Tanpura** | Indian drone instrument providing harmonic foundation |
| **Tabla** | Indian paired percussion drums |
| **Santoor** | Indian hammered dulcimer |
| **FluidSynth** | Open-source software synthesizer for MIDI → audio |
| **SoundFont (.sf2)** | Sampled instrument sound library used by FluidSynth |
| **α-Helix** | Right-handed spiral secondary structure motif in proteins |
| **β-Sheet** | Flat hydrogen-bonded strand secondary structure motif |
| **Sonification** | Converting non-audio data into sound for analysis/communication |

---

*© BioNMR IITG · Cosmic Raga Molecular Sonification Studio*
