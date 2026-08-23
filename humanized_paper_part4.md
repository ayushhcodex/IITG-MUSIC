## 4. Software Architecture and Composition

The project splits into a Python processing backend and a web-based frontend. Once the notes are quantized, the Python backend constructs a 5-track MIDI composition. Designing this multi-track structure took a lot of experimentation, but these five specific instruments create a rich and pleasant soundscape:

- **Track 0 (Santoor):** Plays the primary quantized notes. One note per residue.
- **Track 1 (Bansuri):** Plays an octave lower on a delay to create a natural echo.
- **Track 2 (Sitar):** Hits an accent note every eighth residue to mark structural sequences.
- **Track 3 (Tanpura):** Plays a continuous harmonic drone on the root notes, grounding the piece.
- **Track 4 (Tabla):** Drives a 16-beat Teentaal rhythm.

We feed this complete MIDI file into FluidSynth using a custom SoundFont (\(`TimGM6mb.sf2`\)). FluidSynth renders the MIDI into a high-quality WAV audio file.

On the frontend, a 3D WebGL molecular viewer runs in the browser. When the user hits play, the browser fetches the WAV file. As the audio plays, the viewer highlights the exact amino acid producing that sound on the 3D protein model. We built a live Heads-Up Display (HUD) that shows the current residue, the musical note, and the underlying frequency data. Keeping the 3D molecular viewer and the audio playback perfectly synced in the browser was one of the trickiest parts of this project, but it makes the data easy to follow.
