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
