# Cosmic Raga: A Sonification Framework for NMR Chemical Shifts and Protein Topology

## Abstract

We built a data pipeline that translates molecular protein structures into audio. The system maps Nuclear Magnetic Resonance (NMR) chemical shifts into musical notes. Visualizing complex 2D protein data hides subtle anomalies. By converting tabular data into a synchronized audio-visual stream, researchers can hear structural transitions in real-time. We designed this framework to maintain strict scientific fidelity while producing a listenable, multi-track composition.

## 1. Introduction

Structural biologists rely heavily on visual plotting. When analyzing protein structures using NMR spectroscopy, researchers study dense 2D scatter plots from HSQC experiments. Each dot represents an amino acid residue. Scanning these plots tires the eyes. Spotting localized structural changes across hundreds of residues takes intense focus.

Human hearing excels at recognizing temporal patterns and sudden shifts. We decided to bridge this gap. We built a system that reads raw chemical shift data, processes it mathematically, and outputs an Indian Classical music composition. Every note corresponds strictly to a measured data point. We built this tool so scientists can hear the data they usually only see.

## 2. Materials and Data Processing

The system pulls dataset files from the Biological Magnetic Resonance Data Bank (BMRB) and the Protein Data Bank (PDB). We extract the amino acid sequence, NMR frequencies, and secondary structure into a clean tabular format.

An NMR experiment generates two distinct frequency coordinates for each residue: a Hydrogen shift (¹H) and a Nitrogen shift (¹⁵N). We measure these in parts per million (ppm). To use them mathematically, we convert the ppm values into Hertz based on the spectrometer's baseline power.

\[ f_H = \text{shift}_H \times 750 \text{ MHz} \]
\[ f_N = \text{shift}_N \times 75 \text{ MHz} \]

We combine these dimensions into a single effective frequency. We calculate the geometric mean to fuse the two values without letting one dominate the other.

\[ f_{\text{effective}} = \sqrt{f_H \times f_N} \]

This effective frequency acts as the primary data point for sonification.

## 3. Sonification Methodology

### Log-Exponential Frequency Scaling

The raw effective frequencies sit between 6,500 and 8,800 Hz. You cannot just play these as audio. They sit outside standard musical registers and sound grating. We run the raw values through a log-exponential scaling function to fix this.

Human pitch perception works logarithmically. An octave always represents a doubling of frequency. Our exponential transform keeps the relative contrast of the biological data intact while dropping the output into a listenable 240–480 Hz range.

We normalize the effective frequency \( x \) to a 0 to 1 scale:

\[ x_{\text{norm}} = \frac{x - x_{\text{min}}}{x_{\text{max}} - x_{\text{min}}} \]

We apply an exponential curve:

\[ x_{\text{scaled}} = \frac{e^{x_{\text{norm}}} - 1}{e - 1} \]

We project this scaled value onto our target musical frequency range:

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

We wrote the logic to guarantee it never reorders the data. A higher chemical shift always yields a higher pitch. The rounding just forces the output into a strict musical structure. That part is harder than it sounds. If you mess up the mapping, you ruin the scientific fidelity of the entire project.

### Encoding Protein Topology into Tempo

Proteins fold into physical shapes like alpha helices and beta sheets. We map these structural states to the track tempo. An alpha helix plays at 60 beats per minute. A beta sheet jumps to 80 beats per minute. A random coil slows down to 50 beats per minute. 

A listener hears the protein's physical shape change in real-time. The rhythm itself encodes the 3D topology.

### Deterministic Dynamics and Structural Tension

To guarantee scientific reproducibility, the pseudo-random engine is seeded deterministically using a hash of the amino acid sequence. We map the volume (velocity) of each note using a **deviation score**, which measures how much a residue's frequency diverges from the mean frequency of its specific amino acid type:

\[ \text{deviation}_i = | f_i - \bar{f}_{\text{aa}} | \]

We quantify the local **structural tension** using a rolling variance of the deviation (window size 5):

\[ \text{tension}_i = \text{Var}(\text{deviation}_{i-2} \dots \text{deviation}_{i+2}) \]

During final audio mixing, this tension applies a hyperbolic tangent (tanh) distortion to the rhythmic layers, giving chaotic regions a grittier acoustic texture:

\[ \text{audio}_{\text{distorted}} = \tanh \left( \text{audio}_{\text{raw}} \times (1 + \text{tension}_i \times 15) \right) \]

### Acoustic Smoothing via LFO Filters

To ensure a soothing acoustic experience, we continuously modulate a low-pass filter using a Low-Frequency Oscillator (LFO). Each secondary structure receives a base cutoff (e.g., 110 for Beta sheets, 40 for Random coils). We apply a 0.25 Hz sine wave wobble:

\[ \text{cutoff}_i = \text{cutoff}_{\text{base}} + 15 \times \sin(2 \pi \times 0.25 \times t_i) \]

This cutoff is injected as MIDI Control Change 74 (CC74), stripping away the synthetic "MIDI" sound in favor of an organic, breathing timbre.

## 4. Software Architecture and Composition

The project splits into a Python processing backend and a web-based frontend. Once the notes are quantized, the Python backend constructs a 5-track MIDI composition. 

- **Track 0 (Santoor):** Plays the primary quantized notes. One note per residue.
- **Track 1 (Bansuri):** Plays an octave lower on a delay to create a natural echo.
- **Track 2 (Sitar):** Hits an accent note every eighth residue to mark structural sequences.
- **Track 3 (Tanpura):** Plays a continuous harmonic drone on the root notes, grounding the piece.
- **Track 4 (Tabla):** Drives a 16-beat Teentaal rhythm.

We feed this complete MIDI file into FluidSynth using a custom SoundFont (`TimGM6mb.sf2`). FluidSynth renders the MIDI into a high-quality WAV audio file.

On the frontend, a 3D WebGL molecular viewer runs in the browser. When the user hits play, the browser fetches the WAV file. As the audio plays, the viewer highlights the exact amino acid producing that sound on the 3D protein model. We built a live Heads-Up Display (HUD) that shows the current residue, the musical note, and the underlying frequency data. The audio and the visual model stay locked together.

## 5. Discussion and Results

The resulting system turns static tabular data into a time-series audio stream. Researchers can listen to a protein sequence and hear structural transitions. A sudden tempo shift flags a change from an alpha helix to a beta sheet. A sharp jump in pitch highlights an outlier in the chemical shift data.

We designed the pipeline to operate autonomously. A user inputs a BMRB ID, and the system handles data fetching, mathematical scaling, MIDI generation, and audio rendering. The math stays rigorous, but the output becomes an interactive analytical tool.

## 6. Conclusion

Sonification provides a complementary tool for structural biology. By mapping NMR chemical shifts to musical parameters, we offer researchers a new way to interact with their data. The Cosmic Raga framework proves that scientific accuracy and musicality can coexist. This approach opens doors for faster pattern recognition and anomaly detection in complex molecular datasets.
