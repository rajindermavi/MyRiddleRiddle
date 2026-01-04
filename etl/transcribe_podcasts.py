import json
from pathlib import Path
from typing import Dict, Any, List
from faster_whisper import WhisperModel
from utilities.utility import get_prior_metadata, merge_metadata, save_json

MODEL_SIZE = "small"  # good balance for CPU


def transcribe_audio(
    audio_path: Path,
    model_size: str = MODEL_SIZE,
    device: str = "cpu",
    compute_type: str = "int8",
    word_timestamps: bool = False
) -> Dict[str, Any]:
    """
    Transcribe a single audio file using Whisper.

    Args:
        audio_path: Path to the audio file
        model_size: Whisper model size (tiny, base, small, medium, large)
        device: Device to use (cpu, cuda)
        compute_type: Compute type (int8, float16, float32)
        word_timestamps: Enable word-level timestamps

    Returns:
        Dictionary containing transcription metadata and segments
    """
    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type
    )

    segments, info = model.transcribe(
        str(audio_path),
        word_timestamps=word_timestamps
    )

    # Convert segments to list of dicts with full metadata
    segment_list = []
    for seg in segments:
        segment_dict = {
            "id": seg.id,
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "avg_logprob": seg.avg_logprob,
            "no_speech_prob": seg.no_speech_prob,
            "compression_ratio": seg.compression_ratio,
        }

        # Add optional fields if they exist
        if hasattr(seg, 'temperature') and seg.temperature is not None:
            segment_dict["temperature"] = seg.temperature

        if hasattr(seg, 'seek'):
            segment_dict["seek"] = seg.seek

        # Add word-level timestamps if available
        if hasattr(seg, 'words') and seg.words:
            segment_dict["words"] = [
                {
                    "word": word.word,
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability
                }
                for word in seg.words
            ]

        segment_list.append(segment_dict)

    # Calculate speech ratio
    speech_ratio = None
    if info.duration and info.duration > 0:
        speech_ratio = info.duration_after_vad / info.duration if info.duration_after_vad else None

    return {
        "audio_path": str(audio_path),
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "duration_after_vad": info.duration_after_vad,
        "speech_ratio": speech_ratio,
        "all_language_probs": info.all_language_probs if hasattr(info, 'all_language_probs') and info.all_language_probs else None,
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

    prior_metadata, _ = get_prior_metadata(output_metadata_path)

    # Load podcast metadata
    with metadata_path.open('r', encoding='utf-8') as f:
        podcasts = json.load(f)

    if not podcasts:
        print("No podcasts found in metadata file.")
        return

    existing_transcripts_by_audio_path: Dict[Path, Path] = {}
    for entry in prior_metadata:
        file_path_raw = entry.get("file_path")
        transcript_path_raw = entry.get("transcript_path")
        if not file_path_raw or not transcript_path_raw:
            continue
        transcript_path = Path(transcript_path_raw)
        if transcript_path.exists():
            existing_transcripts_by_audio_path[Path(file_path_raw).resolve()] = transcript_path

    transcription_results = []

    for i, podcast in enumerate(podcasts, 1):
        audio_path = Path(podcast['file_path'])
        audio_resolved = audio_path.resolve()

        if not audio_path.exists():
            print(f"Warning: Audio file not found: {audio_path}")
            continue

        transcript_path = existing_transcripts_by_audio_path.get(audio_resolved) or output_dir / (audio_path.stem + ".json")

        if transcript_path.exists():
            print(f"\n[{i}/{len(podcasts)}] Skipping transcription (already exists): {transcript_path}")
            try:
                with transcript_path.open('r', encoding='utf-8') as tf:
                    existing_data = json.load(tf)
                transcription_results.append({
                    **podcast,
                    "transcript_path": str(transcript_path),
                    "language": existing_data.get("language"),
                    "language_probability": existing_data.get("language_probability"),
                    "num_segments": len(existing_data.get("segments", {}))
                })
            except Exception as exc:
                print(f"Warning: Failed to load existing transcript {transcript_path}: {exc}")
                transcription_results.append({
                    **podcast,
                    "transcript_path": str(transcript_path)
                })
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
        print(f"Duration: {result['duration']:.2f}s (speech: {result['duration_after_vad']:.2f}s, ratio: {result['speech_ratio']:.2%})")
        print(f"Segments: {len(result['segments'])}")

        # Save individual transcription to JSON file
        transcript_filename = audio_path.stem + ".json"
        transcript_path = output_dir / transcript_filename

        # Build segments dictionary with full metadata
        segments_dict = {}
        for idx, seg in enumerate(result['segments'], 1):
            seg_data = {
                'id': seg['id'],
                'text': seg['text'],
                'duration': seg['end'] - seg['start'],
                'start': seg['start'],
                'end': seg['end'],
                'avg_logprob': seg['avg_logprob'],
                'no_speech_prob': seg['no_speech_prob'],
                'compression_ratio': seg['compression_ratio']
            }

            # Add optional fields if present
            if 'temperature' in seg:
                seg_data['temperature'] = seg['temperature']

            if 'seek' in seg:
                seg_data['seek'] = seg['seek']

            if 'words' in seg:
                seg_data['words'] = seg['words']

            segments_dict[f's{idx}'] = seg_data

        transcript_data = {
            'language': result['language'],
            'language_probability': result['language_probability'],
            'duration': result['duration'],
            'duration_after_vad': result['duration_after_vad'],
            'speech_ratio': result['speech_ratio'],
            'segments': segments_dict
        }

        # Add all_language_probs if available
        if result['all_language_probs']:
            transcript_data['all_language_probs'] = result['all_language_probs']

        with transcript_path.open('w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=2)

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
    output_metadata_path.parent.mkdir(parents=True, exist_ok=True)
    combined_metadata = merge_metadata(prior_metadata, transcription_results)
    save_json(combined_metadata, output_metadata_path)

    print(f"\n✓ Transcribed {len(transcription_results)} podcast(s)")
    print(f"✓ Saved transcription metadata to: {output_metadata_path}")
