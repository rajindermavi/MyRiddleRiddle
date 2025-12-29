import json
from pathlib import Path

from riddle_scoring import riddle_scoring

from config import (
    STG_2_META,
    STG_3_DIR,
    STG_3_META
)

def extract_riddles():
    # Load podcast metadata
    with STG_2_META.open('r', encoding='utf-8') as meta_file:
        transcript_meta = json.load(meta_file)

    for meta in transcript_meta:
        transcript_path = Path(meta['transcript_path'])

        with transcript_path.open('r', encoding='utf-8') as transcript_file:
            transcript = json.load(transcript_file)
        
        scored_transcript = riddle_scoring(transcript)

        scored_transcript_path = STG_3_DIR / transcript_path.name

        with scored_transcript_path.open('w', encoding='utf-8') as f:
            json.dump(scored_transcript, f, indent=2)
    
        meta['score_path'] = str(scored_transcript_path)

    with STG_3_META.open('w', encoding='utf-8') as f:
        json.dump(transcript_meta, f, indent=2)

if __name__ == '__main__':
    extract_riddles()