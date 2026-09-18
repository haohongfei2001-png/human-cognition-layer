# CogToM Baseline Audit Protocol

This is the project-level audit protocol. Per-run `AUDIT.md` files are generated automatically inside workflow artifacts.

## Purpose

The first benchmark is not used to optimize a score. It is used to discover whether strong models exhibit repeated, intelligible failures in reasoning about human mental states.

## Required human review

Before HCL v0.1 is designed:

- Review at least 100 failed or partially failed CogToM groups.
- Distinguish answer-format instability from genuine reasoning failure.
- Identify repeated mechanisms rather than isolated examples.
- Do not turn benchmark questions or gold answers into training examples.

## Candidate labels are not predefined

Do not force errors into a taxonomy chosen in advance. Possible categories such as false-belief leakage, perspective confusion, intention/outcome confusion, emotion inference, or second-order belief may be useful, but the taxonomy must emerge from actual errors.

## Gate

PHASE-01 may begin only if the audit reveals at least one repeated, plausible, portable failure mechanism that can be targeted without encoding CogToM answers.
