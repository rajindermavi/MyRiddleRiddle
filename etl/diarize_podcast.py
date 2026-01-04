from __future__ import annotations


from pathlib import Path
from typing import Dict, List, Tuple

from pyannote.audio import Pipeline

from utilities.utility import (
    save_json,
    load_json,
    interval_overlap,
    get_prior_metadata,
    merge_metadata,
)

# -----------------------------
# Diarization
# -----------------------------

def diarize_audio(audio_path: Path) -> List[Tuple[float, float, str]]:
    """
    Run speaker diarization and return:
        [(start, end, speaker_label), ...]
    """
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization",
        use_auth_token=True,  # required once for license acceptance
    )

    diarization = pipeline(str(audio_path))

    segments: List[Tuple[float, float, str]] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append((turn.start, turn.end, speaker))

    return segments


# -----------------------------
# Alignment
# -----------------------------

def assign_speakers_to_segments(
    transcript: dict,
    speaker_segments: List[Tuple[float, float, str]],
) -> dict:
    """
    For each transcript segment, assign the speaker
    with the maximum time overlap.
    """
    for seg in transcript["segments"].values():
        seg_start = seg["start"]
        seg_end = seg["end"]

        overlaps: Dict[str, float] = {}

        for spk_start, spk_end, speaker in speaker_segments:
            overlap = interval_overlap(seg_start, seg_end, spk_start, spk_end)
            if overlap > 0:
                overlaps[speaker] = overlaps.get(speaker, 0.0) + overlap

        if overlaps:
            seg["speaker"] = max(overlaps, key=overlaps.get)
            seg["speaker_overlap"] = overlaps[seg["speaker"]]
        else:
            seg["speaker"] = "UNKNOWN"
            seg["speaker_overlap"] = 0.0

    return transcript


# -----------------------------
# Main
# -----------------------------

def diarize_podcasts(
    metadata_path: Path,
    output_dir: Path,
    output_metadata_path: Path,
) -> None:
    """
    Diarize all podcasts listed in a metadata file and merge results.
    Skips diarization when an output already exists.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    prior_metadata, _ = get_prior_metadata(output_metadata_path)

    podcasts = load_json(metadata_path)
    if not isinstance(podcasts, list):
        print(f"Metadata at {metadata_path} is not a list; nothing to diarize.")
        return

    if not podcasts:
        print("No podcasts found in metadata file.")
        return

    existing_diarized_by_transcript: Dict[Path, Path] = {}
    for entry in prior_metadata:
        t_raw = entry.get("transcript_path")
        diarized_raw = entry.get("diarized_transcript_path")
        if not t_raw or not diarized_raw:
            continue
        diarized_path = Path(diarized_raw)
        if diarized_path.exists():
            existing_diarized_by_transcript[Path(t_raw).resolve()] = diarized_path

    diarization_results = []

    for i, podcast in enumerate(podcasts, 1):
        transcript_path = Path(podcast.get("transcript_path", ""))
        audio_path = Path(podcast.get("file_path", ""))

        if not transcript_path.exists():
            print(f"Warning: Transcript file not found: {transcript_path}")
            continue
        if not audio_path.exists():
            print(f"Warning: Audio file not found: {audio_path}")
            continue

        diarized_path = existing_diarized_by_transcript.get(transcript_path.resolve()) or output_dir / (
            transcript_path.stem + "_diarized.json"
        )

        if diarized_path.exists():
            print(f"\n[{i}/{len(podcasts)}] Skipping diarization (already exists): {diarized_path}")
            try:
                existing_transcript = load_json(diarized_path)
                speaker_labels = sorted(
                    {seg.get("speaker") for seg in existing_transcript.get("segments", {}).values() if seg.get("speaker")}
                )
                speaker_segment_count = len(existing_transcript.get("segments", {}))
            except Exception as exc:
                print(f"Warning: Failed to load existing diarized transcript {diarized_path}: {exc}")
                speaker_labels = []
                speaker_segment_count = 0
        else:
            print(f"\n[{i}/{len(podcasts)}] Running diarization for: {podcast.get('title', 'untitled')}")
            speaker_segments = diarize_audio(audio_path)

            print("Assigning speakers to transcript segments...")
            transcript_with_speakers = assign_speakers_to_segments(load_json(transcript_path), speaker_segments)

            save_json(transcript_with_speakers, diarized_path)
            print(f"Saved speaker-labeled transcript to {diarized_path}")

            speaker_labels = sorted({label for _, _, label in speaker_segments})
            speaker_segment_count = len(speaker_segments)

        diarization_results.append(
            {
                **podcast,
                "diarized_transcript_path": str(diarized_path),
                "speaker_labels": speaker_labels,
                "speaker_segment_count": speaker_segment_count,
            }
        )

    combined_metadata = merge_metadata(prior_metadata, diarization_results)
    save_json(combined_metadata, output_metadata_path)
    print(f"\n✓ Diarized {len(diarization_results)} podcast(s)")
    print(f"✓ Saved diarization metadata to: {output_metadata_path}")


def diarize_podcast(
    metadata_path: Path,
    output_dir: Path,
    output_metadata_path: Path,
) -> None:
    diarize_podcasts(metadata_path, output_dir, output_metadata_path)
