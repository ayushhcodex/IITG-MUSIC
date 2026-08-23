# MrFold Music: A Sonification Framework for NMR Chemical Shifts and Protein Topology

## Abstract

We built a data pipeline that translates molecular protein structures into audio. The system maps Nuclear Magnetic Resonance (NMR) chemical shifts directly into musical notes. Visualizing complex 2D protein data often hides subtle anomalies. By converting tabular data into a synchronized audio-visual stream, researchers can hear structural transitions in real-time. We designed this framework to maintain strict scientific fidelity while producing a listenable, multi-track composition.

## 1. Introduction

Structural biologists lean on visual plotting. When analyzing protein structures using NMR spectroscopy, researchers study dense 2D scatter plots from HSQC experiments. Each dot represents an amino acid residue. Scanning these plots tires the eyes. Spotting localized structural changes across hundreds of residues takes intense focus. That part is harder than it sounds.

Human hearing excels at recognizing temporal patterns and sudden shifts. We decided to bridge this gap. We built a system that reads raw chemical shift data, runs calculations on it, and outputs an Indian Classical music composition. Every note matches a measured data point. We built this tool so scientists can hear the data they normally only see.

Our system does not just assign random pitches. We map the chemical shifts of hydrogen and nitrogen into a single effective frequency, scale it to a listenable register, and snap the notes to an Indian Classical Raag. By doing this, we keep the data's relative order intact while making the output sound musical. We also map the protein's physical shape—like alpha helices and beta sheets—to the tempo, and structural tension to audio distortion. This means you can hear when a protein folds, stretches, or breaks.

## 2. Materials and Data Processing

We pull dataset files from two main databases: the Biological Magnetic Resonance Data Bank (BMRB) and the Protein Data Bank (PDB). We extract the amino acid sequence, the NMR frequencies, and the secondary structure. Getting these databases to talk to each other without breaking the alignment is always a headache, but clean data is crucial here. Once aligned, we clean and merge them into a single table.

An NMR experiment generates two distinct frequency coordinates for each residue. We get a Hydrogen shift (\({}^1\text{H}\)) and a Nitrogen shift (\({}^{15}\text{N}\}), both measured in parts per million (ppm). We convert these ppm values into Hertz based on the baseline power of the spectrometer:

\[ f_H = \text{shift}_H \times 750 \text{ MHz} \]
\[ f_N = \text{shift}_N \times 75 \text{ MHz} \]

Next, we combine these two dimensions into a single effective frequency. We calculate the geometric mean to fuse the values without letting the larger Hydrogen shift dominate:

\[ f_{\text{effective}} = \sqrt{f_H \times f_N} \]

This effective frequency acts as our primary data point for the music pipeline.

## 3. Sonification Methodology

### Log-Exponential Frequency Scaling

The raw effective frequencies sit between 6,500 and 8,800 Hz. If you play these directly as audio, they sound terrible and sit outside standard musical registers. To fix this, we scale them to a listenable 240–480 Hz range.

Human pitch perception works logarithmically. An octave represents a doubling of frequency. Because of this, we use an exponential transform. This preserves the relative contrast of the biological data while dropping the output into a comfortable range.

First, we normalize the effective frequency \( x \) to a 0 to 1 scale:

\[ x_{\text{norm}} = \frac{x - x_{\text{min}}}{x_{\text{max}} - x_{\text{min}}} \]

Next, we apply an exponential curve:

\[ x_{\text{scaled}} = \frac{e^{x_{\text{norm}}} - 1}{e - 1} \]

Finally, we project this scaled value onto our target musical frequency range:

\[ f_{\text{musical}} = f_{\text{min}} + x_{\text{scaled}} \times (f_{\text{max}} - f_{\text{min}}) \]

### MIDI Mapping and Raag Quantization

We use the standard conversion formula to find the exact MIDI note for our scaled frequency:

\[ \text{MIDI}_{\text{raw}} = 69 + 12 \times \log_2 \left( \frac{f_{\text{musical}}}{440} \right) \]

A raw mapped MIDI note might land between standard piano keys. We handle this by quantizing the notes to an Indian Classical Raag scale, like Yaman or Bhairav. A Raag defines specific permitted semitone intervals from a root note.

Our algorithm grabs the raw MIDI note and snaps it to the nearest allowed semitone in the chosen Raag.

1. Find the degree within the 12-semitone octave:
\[ \text{degree} = (\text{MIDI}_{\text{raw}} - \text{root}) \bmod 12 \]

2. Search the Raag's permitted intervals to find the closest match:
\[ \text{interval}_{\text{closest}} = \text{argmin}_{i \in \text{Raag}} \, |i - \text{degree}| \]

3. Snap the raw note to this closest interval:
\[ \text{MIDI}_{\text{quantized}} = \text{MIDI}_{\text{raw}} - \text{degree} + \text{interval}_{\text{closest}} \]

We wrote the logic to guarantee it never reorders the data. A higher chemical shift always yields a higher pitch. The rounding just forces the output into a strict musical structure. If you mess up the mapping, you ruin the scientific fidelity of the entire project. That is a mistake that is surprisingly easy to make.

### Encoding Protein Topology into Tempo

Proteins fold into physical shapes like alpha helices and beta sheets. We map these structural states to the track tempo. An alpha helix plays at 60 beats per minute. A beta sheet jumps to 80 beats per minute. A random coil slows down to 50 beats per minute. 

A listener hears the protein's physical shape change in real-time. The rhythm itself encodes the 3D topology.

### Deterministic Dynamics and Structural Tension

To guarantee scientific reproducibility, we seed the pseudo-random engine using a hash of the amino acid sequence. We map the volume (velocity) of each note using a deviation score, which measures how much a residue's frequency diverges from the mean frequency of its specific amino acid type:

\[ \text{deviation}_i = | f_i - \bar{f}_{\text{aa}} | \]

We quantify the local structural tension using a rolling variance of the deviation (window size 5):

\[ \text{tension}_i = \text{Var}(\text{deviation}_{i-2} \dots \text{deviation}_{i+2}) \]

During final audio mixing, this tension applies a hyperbolic tangent (tanh) distortion to the rhythmic layers, giving chaotic regions a grittier acoustic texture:

\[ \text{audio}_{\text{distorted}} = \tanh \left( \text{audio}_{\text{raw}} \times (1 + \text{tension}_i \times 15) \right) \]

### Acoustic Smoothing via LFO Filters

To ensure a soothing acoustic experience, we continuously modulate a low-pass filter using a Low-Frequency Oscillator (LFO). Each secondary structure receives a base cutoff (e.g., 110 for Beta sheets, 40 for Random coils). We apply a 0.25 Hz sine wave wobble:

\[ \text{cutoff}_i = \text{cutoff}_{\text{base}} + 15 \times \sin(2 \pi \times 0.25 \times t_i) \]

This cutoff is injected as MIDI Control Change 74 (CC74), stripping away the synthetic digital sound in favor of an organic, breathing timbre. Getting a standard digital synthesizer to sound like an organic instrument requires some tricks, and this LFO modulation does the heavy lifting.

## 4. Software Architecture and Composition

The project splits into a Python processing backend and a web-based frontend. Once the notes are quantized, the Python backend constructs a 5-track MIDI composition. Designing this multi-track structure took a lot of experimentation, but these five specific instruments create a rich and pleasant soundscape:

- **Track 0 (Santoor):** Plays the primary quantized notes. One note per residue.
- **Track 1 (Bansuri):** Plays an octave lower on a delay to create a natural echo.
- **Track 2 (Sitar):** Hits an accent note every eighth residue to mark structural sequences.
- **Track 3 (Tanpura):** Plays a continuous harmonic drone on the root notes, grounding the piece.
- **Track 4 (Tabla):** Drives a 16-beat Teentaal rhythm.

We feed this complete MIDI file into FluidSynth using a custom SoundFont (\(`TimGM6mb.sf2`\)). FluidSynth renders the MIDI into a high-quality WAV audio file.

On the frontend, a 3D WebGL molecular viewer runs in the browser. When the user hits play, the browser fetches the WAV file. As the audio plays, the viewer highlights the exact amino acid producing that sound on the 3D protein model. We built a live Heads-Up Display (HUD) that shows the current residue, the musical note, and the underlying frequency data. Keeping the 3D molecular viewer and the audio playback perfectly synced in the browser was one of the trickiest parts of this project, but it makes the data easy to follow.

## 5. Discussion and Results

The system turns static tables into a time-series audio stream. Researchers can listen to a protein sequence and hear structural transitions. A sudden tempo shift flags a change from an alpha helix to a beta sheet. A sharp jump in pitch highlights an outlier in the chemical shift data. We were surprised by how quickly the human ear catches a bad data point when listening, compared to searching through spreadsheets.

We designed the pipeline to run on its own. A user inputs a BMRB ID, and the system handles data fetching, scaling, MIDI generation, and audio rendering. The math stays rigorous, but the output becomes an interactive tool. It takes some getting used to, but after a few tracks, you start recognizing the signature sounds of different structures.

## 6. Conclusion

Sonification offers a useful secondary tool for structural biology. By mapping NMR chemical shifts to musical parameters, we give researchers a new way to interact with their data. The MrFold Music framework proves that scientific accuracy and musicality can work together. This approach opens doors for faster pattern recognition and finding anomalies in complex molecular datasets. There is still plenty of room to expand this, but the core system shows that sonification has a real place in modern lab work.
