# Architecture.md — Pipeline Structure and Data Flow

## Overview

The system is implemented as a **linear, disk-backed pipeline** composed of small, single-responsibility modules.

Each stage:
- Consumes artifacts from the previous stage
- Produces structured output to disk
- Does not mutate upstream data

Re-running any stage must not require re-running earlier stages unless inputs change.

---

## Stage-by-Stage Architecture

## High-Level Pipeline

RSS Feed

Audio Download

Audio Normalization

ASR (Timestamped Transcription)

Speaker Diarization

Segment Scoring (Riddle-likeness)

Riddle Extraction

Answer Candidate Extraction

Riddle–Answer Association


Each stage emits structured artifacts (JSON / JSONL) to disk.

---

## Pipeline Stages

### 1. Podcast Acquisition

**Input**
- RSS feed URL

**Output**
- Audio files (e.g. `.mp3`, `.m4a`)
- Episode metadata (title, date, duration)

**Notes**
- Episodes are immutable once downloaded
- Filenames include episode ID and publish date

---

### 2. ASR (Transcription)

**Module**
- `transcribe.py`

**Inputs**
- MP3 files

**Outputs**
- Timestamped transcript JSON

**Transcript Schema (Conceptual)**

```json
{
  "segments": [
    {
      "id": "s123",
      "start": 12.3,
      "end": 18.7,
      "text": "...",
      "confidence": 0.94
    }
  ]
}

---

### 3. Speaker Diarization

**Purpose**
- Associate transcript segments with speakers

**Output**
- Speaker-labeled segments:
  - `speaker_id`
  - time boundaries
  - confidence (if available)

**Notes**
- Exact speaker identity is not required
- Consistency within an episode matters more than cross-episode identity

---

### 4. Segment Scoring (Riddle-likeness)

Each transcript segment is scored along several heuristic axes.

**Example Signals**
- Presence of a question mark
- Interrogative phrasing
- Abstract or metaphorical language
- Invitations to guess or think
- Length constraints (not too short, not too long)
- Repetition or rephrasing patterns

**Output**
- Augmented transcript with per-segment scores:
  ```json
  {
    "segment_id": "...",
    "scores": {
      "question_likeness": 0.0–1.0,
      "abstraction": 0.0–1.0,
      "invites_guessing": 0.0–1.0,
      "length_score": 0.0–1.0,
      "overall_riddle_score": 0.0–1.0
    }
  }

### 5. Riddle Extraction

**Purpose**

- Identify contiguous segments that form a single riddle

**Approach**

- Threshold on riddle-likeness score
- Merge adjacent high-scoring segments
- Allow for brief interruptions or jokes

**Output**

- Riddle objects:

{
  "riddle_id": "...",
  "start_time": ...,
  "end_time": ...,
  "text": "...",
  "speaker_ids": [...],
  "source_segments": [...]
}

### 6. Answer Candidate Extraction

**Purpose**

-Identify short utterances that could be answers

**Heuristics**

- Short noun phrases
- Unexpected lexical items
- Repeated guesses by different speakers
- Responses following riddle segments

**Output**

- Candidate answers with timestamps and speaker info

### 7. Riddle–Answer Association

**Purpose**

- Link candidate answers to riddles

**Signals**

- Temporal proximity
- Speaker turn-taking patterns
- Explicit confirmation phrases
- Repetition or emphasis

**Output**

- Riddle objects enriched with:
  - Candidate answers
  - Confidence scores
  - (Optional) selected “best” answer