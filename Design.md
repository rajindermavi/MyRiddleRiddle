# Design.md — Semantic Riddle Extraction from Podcast Audio

## Project Summary

This project is a **local-first research pipeline** for converting conversational podcast audio into **structured semantic data**, with a specific focus on **riddle extraction and answer association**.

The source material is a recurring riddle-themed podcast where riddles are embedded in informal dialogue rather than clearly marked segments.

The output is a structured dataset containing:
- Riddle text
- Candidate answers
- Likely correct answers (when detectable)
- Temporal alignment to the source audio

This is not a product or service. It is an exploratory, reproducible research system.

---

## Goals

- Transcribe podcast audio into timestamped text
- Identify segments likely to contain riddles
- Extract riddles spanning one or more segments
- Identify and associate possible answers
- Preserve intermediate artifacts for analysis and iteration

---

## Non-Goals

- No GUI or frontend
- No real-time processing
- No cloud-based ML or inference APIs
- No requirement for perfect accuracy
- No attempt at full generalization beyond the target podcast

---

## Design Principles

- **Local-first**: All processing runs on a single machine
- **Modular**: Each stage can be rerun independently
- **Inspectable**: Every stage emits readable artifacts
- **Incremental**: Partial success is acceptable
- **Deterministic where possible**: Reproducibility preferred over novelty

---

## Constraints

- Hardware:
  - Intel i5 CPU
  - 8 GB RAM
  - Ubuntu Linux
- No GPU
- No external inference services
- Prefer open-source tools
- Slow processing is acceptable; unbounded processing is not

---

## Conceptual Pipeline

1. Acquire podcast audio
2. Normalize audio
3. Generate timestamped transcripts
4. Assign speaker labels
5. Score transcript segments for “riddle-ness”
6. Extract riddles
7. Extract candidate answers
8. Associate answers to riddles

Each stage refines structure without destroying earlier information.

---

## Evaluation Philosophy

- Qualitative evaluation via manual inspection
- Explainability over raw accuracy
- Ability to trace every decision back to transcript evidence

---

## Explicitly Out of Scope

- Training large neural models from scratch
- UI/UX considerations
- Deployment or scaling concerns
- Monetization

---

## Summary

This project treats podcast audio as a **semantic signal stream**, not just text. Its core value lies in **transparent intermediate representations** and **iterative reasoning**, rather than end-to-end black-box inference.
