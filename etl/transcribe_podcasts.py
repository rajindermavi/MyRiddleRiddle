import json
from pathlib import Path
from typing import Dict, Any
from faster_whisper import WhisperModel

MODEL_SIZE = "small"  # good balance for CPU


def transcribe_audio(
    audio_path: Path,
    model_size: str = MODEL_SIZE,
    device: str = "cpu",
    compute_type: str = "int8"
) -> Dict[str, Any]:
    """
    Transcribe a single audio file using Whisper.

    Args:
        audio_path: Path to the audio file
        model_size: Whisper model size (tiny, base, small, medium, large)
        device: Device to use (cpu, cuda)
        compute_type: Compute type (int8, float16, float32)

    Returns:
        Dictionary containing transcription metadata and segments
    """
    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type
    )

    segments, info = model.transcribe(str(audio_path))

    # Convert segments to list of dicts
    segment_list = []
    for seg in segments:
        segment_list.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip()
        })

    return {
        "audio_path": str(audio_path),
        "language": info.language,
        "language_probability": info.language_probability,
        "segments": segment_list
    }


def transcribe_podcasts(
    metadata_path: Path,
    output_dir: Path,
    output_metadata_path: Path,
    model_size: str = MODEL_SIZE,
    device: str = "cpu",
    compute_type: str = "int8"
) -> None:
    """
    Transcribe all podcasts listed in a metadata file.

    Args:
        metadata_path: Path to JSON metadata file containing podcast info
        output_dir: Directory to save transcription files
        output_metadata_path: Path to save transcription metadata
        model_size: Whisper model size
        device: Device to use (cpu, cuda)
        compute_type: Compute type (int8, float16, float32)
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load podcast metadata
    with metadata_path.open('r', encoding='utf-8') as f:
        podcasts = json.load(f)

    if not podcasts:
        print("No podcasts found in metadata file.")
        return

    transcription_results = []

    for i, podcast in enumerate(podcasts, 1):
        audio_path = Path(podcast['file_path'])

        if not audio_path.exists():
            print(f"Warning: Audio file not found: {audio_path}")
            continue

        print(f"\n[{i}/{len(podcasts)}] Transcribing: {podcast['title']}")
        print(f"Audio file: {audio_path}")

        # Transcribe the audio
        result = transcribe_audio(
            audio_path,
            model_size=model_size,
            device=device,
            compute_type=compute_type
        )

        print(f"Language: {result['language']} (probability: {result['language_probability']:.2f})")
        print(f"Segments: {len(result['segments'])}")

        # Save individual transcription to text file
        transcript_filename = audio_path.stem + "_transcript.txt"
        transcript_path = output_dir / transcript_filename

        with transcript_path.open('w', encoding='utf-8') as f:
            for seg in result['segments']:
                f.write(f"[{seg['start']:.2f} → {seg['end']:.2f}] {seg['text']}\n")

        print(f"Saved transcript to: {transcript_path}")

        # Add to results with original podcast metadata
        transcription_results.append({
            **podcast,
            "transcript_path": str(transcript_path),
            "language": result['language'],
            "language_probability": result['language_probability'],
            "num_segments": len(result['segments'])
        })

    # Save transcription metadata
    with output_metadata_path.open('w', encoding='utf-8') as f:
        json.dump(transcription_results, f, indent=2)

    print(f"\n✓ Transcribed {len(transcription_results)} podcast(s)")
    print(f"✓ Saved transcription metadata to: {output_metadata_path}")