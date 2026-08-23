## 5. Discussion and Results

The system turns static tables into a time-series audio stream. Researchers can listen to a protein sequence and hear structural transitions. A sudden tempo shift flags a change from an alpha helix to a beta sheet. A sharp jump in pitch highlights an outlier in the chemical shift data. We were surprised by how quickly the human ear catches a bad data point when listening, compared to searching through spreadsheets.

We designed the pipeline to run on its own. A user inputs a BMRB ID, and the system handles data fetching, scaling, MIDI generation, and audio rendering. The math stays rigorous, but the output becomes an interactive tool. It takes some getting used to, but after a few tracks, you start recognizing the signature sounds of different structures.
