## 2. Materials and Data Processing

We pull dataset files from two main databases: the Biological Magnetic Resonance Data Bank (BMRB) and the Protein Data Bank (PDB). We extract the amino acid sequence, the NMR frequencies, and the secondary structure. Getting these databases to talk to each other without breaking the alignment is always a headache, but clean data is crucial here. Once aligned, we clean and merge them into a single table.

An NMR experiment generates two distinct frequency coordinates for each residue. We get a Hydrogen shift (\({}^1\text{H}\)) and a Nitrogen shift (\({}^{15}\text{N}\)), both measured in parts per million (ppm). We convert these ppm values into Hertz based on the baseline power of the spectrometer:

\[ f_H = \text{shift}_H \times 750 \text{ MHz} \]
\[ f_N = \text{shift}_N \times 75 \text{ MHz} \]

Next, we combine these two dimensions into a single effective frequency. We calculate the geometric mean to fuse the values without letting the larger Hydrogen shift dominate:

\[ f_{\text{effective}} = \sqrt{f_H \times f_N} \]

This effective frequency acts as our primary data point for the music pipeline.
