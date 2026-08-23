import pandas as pd
import numpy as np
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Merge Backbone and Chemical Shift CSVs and convert PPM to Final Freq (Hz)")
    parser.add_argument("--backbone", required=True, help="Path to the Backbone CSV (contains Secondary Structure)")
    parser.add_argument("--shifts", required=True, help="Path to the Chemical Shifts CSV (contains X_shift and Y_shift)")
    parser.add_argument("--spectrometer", type=float, required=True, help="Spectrometer frequency in MHz (e.g., 750, 900)")
    parser.add_argument("--output", required=True, help="Path to save the final merged CSV for sonify.py")
    
    args = parser.parse_args()
    
    try:
        # Load the CSVs
        df_backbone = pd.read_csv(args.backbone)
        df_shifts = pd.read_csv(args.shifts)
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        sys.exit(1)
        
    # Ensure sequence columns exist for merging
    if "sequence" not in df_backbone.columns:
        print("Error: Backbone CSV must contain a 'sequence' column.")
        sys.exit(1)
    if "sequence" not in df_shifts.columns:
        print("Error: Chemical Shifts CSV must contain a 'sequence' column.")
        sys.exit(1)
        
    # Merge the dataframes on 'sequence'
    df_merged = pd.merge(df_shifts, df_backbone[['sequence', 'Secondary Structure']], on="sequence", how="inner")
    
    # Check if necessary columns exist
    if "X_shift" not in df_merged.columns or "Y_shift" not in df_merged.columns:
        print("Error: Chemical Shifts CSV must contain 'X_shift' and 'Y_shift' columns.")
        sys.exit(1)
        
    # Convert PPM to Hertz using the user-provided spectrometer frequency
    spectrometer_mhz = args.spectrometer
    
    # H_Hz = X_shift * spectrometer_mhz
    df_merged["H_Hz"] = df_merged["X_shift"] * spectrometer_mhz
    
    # N_Hz = Y_shift * (spectrometer_mhz / 10.0)
    df_merged["N_Hz"] = df_merged["Y_shift"] * (spectrometer_mhz / 10.0)
    
    # Final_Freq = sqrt(H_Hz * N_Hz)
    df_merged["Final_Freq"] = np.round(np.sqrt(df_merged["H_Hz"] * df_merged["N_Hz"]), 2)
    
    # Select final columns needed for sonify.py
    columns_to_keep = ["sequence", "chem_comp_ID", "X_shift", "Y_shift", "H_Hz", "N_Hz", "Final_Freq", "Secondary Structure"]
    # Filter to only columns that exist
    final_cols = [c for c in columns_to_keep if c in df_merged.columns]
    
    df_final = df_merged[final_cols]

    # Warn if amino acid identity was lost — sonify.py will silently fall back
    # to "ALA" for every residue if chem_comp_ID is absent, which corrupts the
    # deterministic seed and changes the music output.
    if "chem_comp_ID" not in df_final.columns:
        print(
            "WARNING: 'chem_comp_ID' column not found in the merged output.\n"
            "         sonify.py will label every residue as 'ALA', which will\n"
            "         affect the deterministic random seed and alter the music.\n"
            "         Add a 'chem_comp_ID' column to your Chemical Shifts CSV\n"
            "         (three-letter amino acid codes, e.g. ALA, GLY, TRP)."
        )

    df_final.to_csv(args.output, index=False)
    print(f"✅ Successfully processed {len(df_final)} residues using a {spectrometer_mhz} MHz spectrometer.")
    print(f"✅ Saved merged file to: {args.output}")
    print(f"\nYou can now generate music using: python sonify.py {args.output} output_music.mid --wav output_music.wav")


if __name__ == "__main__":
    main()
