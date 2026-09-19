# Case Study — From Field Notes to Defensible Mystery-Shop Report

## Problem

A mystery shopper must visit a bar, behave like a normal guest, assess service and atmosphere, verify payment handling, retain receipt evidence and submit a structured survey within a short deadline. The risk is not analytical complexity; it is missing a small but essential fact, losing evidence, introducing inconsistent amounts, or mixing subjective assumptions with observable facts.

## Approach

The implementation uses a local-first Flask workflow. The shopper captures timing, order/payment details, five observation scores and factual notes. The application normalizes and validates the input, reconciles the expected price, charged amount and receipt amount, calculates a transparent 100-point working score, and applies a separate QA gate.

Receipt/photo evidence is kept outside the public static directory. Images are re-saved without EXIF metadata. Additional photos are rejected by validation unless the assignment is explicitly marked as allowing them. Alcohol orders require an age-eligibility confirmation. A purge script enforces a configurable evidence-retention period.

## Demonstrable results

The included automated test suite verifies the important behaviors rather than inventing client outcomes. The synthetic generator can create reproducible demo records across all six cities listed in the posting. Every generated record is marked `DEMO_ONLY`, which prevents synthetic data from being mistaken for field evidence.

The application exports all records as CSV and each visit as a Markdown working report. These outputs provide a clean handoff into the client's official survey process while keeping the external BARE submission manual until credentials and the exact form schema are supplied.

## Limits

No physical bar visit, client venue, receipt or BARE submission is fabricated. The client guideline referenced in the job post was not present in the provided materials, so the implemented QA rules are a generic operational baseline. In a live assignment, the first configuration step is to map the actual guideline questions and thresholds into `docs/CLIENT_GUIDELINE_MAPPING.md` and the form/validation layer.