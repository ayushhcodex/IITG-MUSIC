import os
import subprocess
import sys

# Resolve the absolute path to sonify.py so this script works correctly
# regardless of the current working directory it is invoked from.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SONIFY_SCRIPT = os.path.join(_HERE, "sonify.py")

input_dir = "sonify_input_csvs"
output_dir = "batch_music_outputs"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

csv_files = [f for f in os.listdir(input_dir) if f.endswith(".csv")]

for csv_file in csv_files:
    base_name = csv_file.replace("_final_freq.csv", "")
    input_path = os.path.join(input_dir, csv_file)
    output_mid_path = os.path.join(output_dir, f"{base_name}.mid")
    output_wav_path = os.path.join(output_dir, f"{base_name}.wav")

    print(f"Processing {base_name}...")
    subprocess.run(
        [sys.executable, _SONIFY_SCRIPT, input_path, output_mid_path, "--wav", output_wav_path],
        check=False
    )

print("Batch processing complete!")
