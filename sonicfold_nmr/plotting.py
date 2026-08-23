"""Pattern plots for MrFold Music NMR sonification datasets.

Example
-------
sonicfold-plot --csv dataset.csv --audio sonification.wav --outdir graphs
"""

from __future__ import annotations

import argparse
import wave
from collections import Counter
from pathlib import Path

import matplotlib

# The tool saves images and must not require a desktop plotting backend.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


STRUCTURE_COLORS = {
    "Alpha helix": "#4C78A8",
    "Beta sheet": "#F58518",
    "Random coil": "#54A24B",
}


def _audio_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def _contiguous_runs(values: pd.Series):
    start = 0
    for index in range(1, len(values) + 1):
        if index == len(values) or values.iloc[index] != values.iloc[start]:
            yield start, index - 1, values.iloc[start]
            start = index


def plot_frequency_pattern(
    data: pd.DataFrame, output: str | Path, seconds_per_row: float | None = None
) -> None:
    """Plot final frequency, structure regions, and exact repeated frequencies."""
    fig, axis = plt.subplots(figsize=(13, 6.5), constrained_layout=True)
    used_labels: set[str] = set()

    for start, end, structure in _contiguous_runs(data["Secondary Structure"]):
        color = STRUCTURE_COLORS.get(structure, "#808080")
        label = structure if structure not in used_labels else None
        used_labels.add(structure)
        axis.axvspan(
            data["sequence"].iloc[start] - 0.5,
            data["sequence"].iloc[end] + 0.5,
            color=color,
            alpha=0.15,
            label=label,
        )

    axis.plot(
        data["sequence"], data["Final_Freq"], color="#222222", linewidth=1.1,
        zorder=2, label="Final frequency",
    )
    value_counts = Counter(data["Final_Freq"])
    repeated = data["Final_Freq"].map(value_counts).gt(1)
    axis.scatter(
        data.loc[repeated, "sequence"], data.loc[repeated, "Final_Freq"],
        s=45, color="#D62728", edgecolor="white", linewidth=0.6, zorder=3,
        label="Exact repeated frequency",
    )

    axis.set_title("Final-frequency pattern across the protein sequence")
    axis.set_xlabel("Residue sequence number")
    axis.set_ylabel("Final frequency (Hz)")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncol=2, loc="upper left", frameon=False)

    if seconds_per_row:
        first_residue = data["sequence"].iloc[0]
        to_time = lambda residue: (residue - first_residue) * seconds_per_row
        to_residue = lambda seconds: seconds / seconds_per_row + first_residue
        top_axis = axis.secondary_xaxis("top", functions=(to_time, to_residue))
        top_axis.set_xlabel("Sonification time (seconds)")

    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_structure_recurrence(
    data: pd.DataFrame, output: str | Path, window: int = 16
) -> None:
    """Plot rolling alpha-helix, beta-sheet, and random-coil composition."""
    if window < 1:
        raise ValueError("window must be at least 1")

    fig, axis = plt.subplots(figsize=(13, 6.5), constrained_layout=True)
    structures = data["Secondary Structure"]

    for structure, color in STRUCTURE_COLORS.items():
        proportion = (structures == structure).rolling(
            window=window, center=True, min_periods=1
        ).mean()
        axis.plot(
            data["sequence"], proportion * 100, linewidth=2.2,
            color=color, label=structure,
        )

    axis.set_title(
        f"Recurring secondary-structure composition ({window}-residue rolling window)"
    )
    axis.set_xlabel("Residue sequence number")
    axis.set_ylabel("Share of residues in window (%)")
    axis.set_ylim(-2, 102)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False, ncol=3, loc="upper center")
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot MrFold Music sonification patterns.")
    parser.add_argument("--csv", type=Path, required=True, help="Input BMRB CSV file")
    parser.add_argument("--audio", type=Path, help="Optional WAV sonification file")
    parser.add_argument("--outdir", type=Path, default=Path("graphs"))
    parser.add_argument("--window", type=int, default=16, help="Rolling window in residues")
    args = parser.parse_args()

    if not args.csv.is_file():
        raise SystemExit(
            f"CSV file not found: {args.csv}. Pass its full path, or place it in "
            "the current project folder and use the exact filename."
        )
    if args.audio and not args.audio.is_file():
        raise SystemExit(
            f"WAV file not found: {args.audio}. Pass its full path, or place it in "
            "the current project folder and use the exact filename."
        )

    try:
        data = pd.read_csv(args.csv)
    except PermissionError as error:
        raise SystemExit(
            f"Cannot read {args.csv}. macOS has blocked this terminal from accessing "
            "the Downloads folder. Grant your terminal Downloads Folder access in "
            "System Settings > Privacy & Security > Files and Folders, or move the "
            "CSV and WAV into this project folder before running the command."
        ) from error
    required_columns = {"sequence", "Final_Freq", "Secondary Structure"}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing_columns))}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.audio:
        try:
            seconds_per_row = _audio_duration_seconds(args.audio) / len(data)
        except PermissionError as error:
            raise SystemExit(
                f"Cannot read {args.audio}. macOS has blocked this terminal from "
                "accessing the Downloads folder. Grant Downloads Folder access to "
                "your terminal or move the WAV into this project folder."
            ) from error
    else:
        seconds_per_row = 0.75
    plot_frequency_pattern(
        data, args.outdir / "frequency_pattern.png", seconds_per_row
    )
    plot_structure_recurrence(
        data, args.outdir / "structure_recurrence.png", args.window
    )
    print(f"Wrote {args.outdir / 'frequency_pattern.png'}")
    print(f"Wrote {args.outdir / 'structure_recurrence.png'}")


if __name__ == "__main__":
    main()
