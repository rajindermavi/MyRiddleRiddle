from __future__ import annotations

import math
from typing import Dict, Any, List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ----------------------------
# Heuristic vocabularies
# ----------------------------

QUESTION_STARTERS = {
    "what", "why", "how", "when", "where", "which",
    "does", "do", "is", "are", "can", "has", "have", "would"
}

ABSTRACT_WORDS = {
    "thing", "something", "nothing", "object",
    "place", "has", "makes", "does", "without"
}

METAPHOR_MARKERS = {
    "but", "without", "yet", "although", "though"
}

GUESS_MARKERS = {
    "guess",
    "what am i",
    "what is it",
    "can you",
    "figure out"
}


# ----------------------------
# Utility functions
# ----------------------------

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def word_count(text: str) -> int:
    return len(text.split())


# ----------------------------
# Embedding + similarity
# ----------------------------

def compute_embeddings(texts: List[str]) -> np.ndarray:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model.encode(texts, normalize_embeddings=True)


def repetition_scores(embeddings: np.ndarray) -> List[float]:
    sim = cosine_similarity(embeddings)
    scores = []

    for i in range(len(sim)):
        # ignore self-similarity
        row = np.delete(sim[i], i)
        scores.append(float(row.max()) if len(row) else 0.0)

    return scores


# ----------------------------
# Scoring per segment
# ----------------------------

def score_segment(
    text: str,
    repetition: float,
    avg_logprob: float | None = None
) -> Dict[str, float]:

    text_l = text.lower()
    words = text_l.split()
    wc = max(len(words), 1)

    has_qmark = 1.0 if "?" in text else 0.0

    questionlike = (
        1.0
        if words and words[0] in QUESTION_STARTERS
        else 0.0
    )

    abstract = sum(w in ABSTRACT_WORDS for w in words) / wc

    metaphor = 1.0 if any(m in text_l for m in METAPHOR_MARKERS) else 0.0

    guessing = 1.0 if any(g in text_l for g in GUESS_MARKERS) else 0.0

    length_score = clamp(1.0 - abs(wc - 15) / 15)

    confidence = (
        clamp(1.0 + avg_logprob) if avg_logprob is not None else 0.5
    )

    total = clamp(
        0.20 * has_qmark +
        0.20 * repetition +
        0.15 * questionlike +
        0.10 * abstract +
        0.10 * metaphor +
        0.10 * guessing +
        0.15 * length_score
    )

    return {
        "has_question_mark": has_qmark,
        "repetition_similarity": repetition,
        "question_likeness": questionlike,
        "abstraction": abstract,
        "metaphorical": metaphor,
        "invites_guessing": guessing,
        "length_score": length_score,
        "asr_confidence": confidence,
        "riddle_score": total,
    }


# ----------------------------
# Main entry point
# ----------------------------

def riddle_scoring(transcript: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input: transcript JSON 
    Output: same structure, but segments rewritten as:
        {
          "s1": {
            "transcription": {...},
            "scoring": {...}
          }
        }
    """

    segments = transcript["segments"]

    segment_ids = list(segments.keys())
    texts = [segments[s]["text"] for s in segment_ids]

    embeddings = compute_embeddings(texts)
    repetition = repetition_scores(embeddings)

    scored_segments = {}

    for idx, seg_id in enumerate(segment_ids):
        seg = segments[seg_id]

        scoring = score_segment(
            text=seg["text"],
            repetition=repetition[idx],
            avg_logprob=seg.get("avg_logprob")
        )

        scored_segments[seg_id] = {
            "transcription": seg,
            "scoring": scoring
        }

    # return full transcript with rewritten segments
    return {
        **{k: v for k, v in transcript.items() if k != "segments"},
        "segments": scored_segments
    }
