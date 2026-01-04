from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

def save_json(data: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_prior_metadata(metadata_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Path]]:
    """Load prior metadata and discover existing files keyed by audio URL."""
    prior_metadata: List[Dict[str, Any]] = []
    existing_files_by_url: Dict[str, Path] = {}
    try:
        loaded_metadata = load_json(metadata_path)
        if isinstance(loaded_metadata, list):
            prior_metadata = loaded_metadata
            print(f"Loaded prior metadata from {metadata_path} ({len(prior_metadata)} entries).")
        else:
            print(f"Metadata at {metadata_path} is not a list; starting fresh.")
    except FileNotFoundError:
        print(f"No prior metadata found at {metadata_path}; starting fresh.")
    except Exception as exc:
        print(f"Failed to load prior metadata from {metadata_path}: {exc}")

    for entry in prior_metadata:
        audio_url = entry.get("audio_url")
        file_path_raw = entry.get("file_path")
        if not audio_url or not file_path_raw:
            continue
        path = Path(file_path_raw)
        if path.exists():
            existing_files_by_url[audio_url] = path

    return prior_metadata, existing_files_by_url


def merge_metadata(prior: List[Dict[str, Any]], new_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge metadata entries preferring newer data on duplicate keys."""
    merged: Dict[str, Dict[str, Any]] = {}

    def entry_key(entry: Dict[str, Any]) -> Optional[str]:
        return entry.get("audio_url") or entry.get("guid") or entry.get("title")

    for entry in prior:
        key = entry_key(entry)
        if key:
            merged[key] = entry

    for entry in new_entries:
        key = entry_key(entry)
        if key:
            merged[key] = entry

    return list(merged.values())


def interval_overlap(a_start: float, a_end: float,
                     b_start: float, b_end: float) -> float:
    """Return overlap duration between intervals A and B."""
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))
