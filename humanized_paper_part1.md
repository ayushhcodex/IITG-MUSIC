# MrFold Music: A Sonification Framework for NMR Chemical Shifts and Protein Topology

## Abstract

We built a data pipeline that translates molecular protein structures into audio. The system maps Nuclear Magnetic Resonance (NMR) chemical shifts directly into musical notes. Visualizing complex 2D protein data often hides subtle anomalies. By converting tabular data into a synchronized audio-visual stream, researchers can hear structural transitions in real-time. We designed this framework to maintain strict scientific fidelity while producing a listenable, multi-track composition.

## 1. Introduction

Structural biologists lean on visual plotting. When analyzing protein structures using NMR spectroscopy, researchers study dense 2D scatter plots from HSQC experiments. Each dot represents an amino acid residue. Scanning these plots tires the eyes. Spotting localized structural changes across hundreds of residues takes intense focus. That part is harder than it sounds.

Human hearing excels at recognizing temporal patterns and sudden shifts. We decided to bridge this gap. We built a system that reads raw chemical shift data, runs calculations on it, and outputs an Indian Classical music composition. Every note matches a measured data point. We built this tool so scientists can hear the data they normally only see.

Our system does not just assign random pitches. We map the chemical shifts of hydrogen and nitrogen into a single effective frequency, scale it to a listenable register, and snap the notes to an Indian Classical Raag. By doing this, we keep the data's relative order intact while making the output sound musical. We also map the protein's physical shape—like alpha helices and beta sheets—to the tempo, and structural tension to audio distortion. This means you can hear when a protein folds, stretches, or breaks.
