# Main integration — 16 September 2026

Merged main at 9b15559 into mixed-work at fe70998. The backup branch
backup/mixed-work-before-main-20260916 preserves the pre-merge tip.

## Resolution

Retained mixed-work's tested agent, tool, persistence and analytics implementations
where main contained older versions of the same features. This preserves explicit
failures, evidence metadata, memory retention, per-turn checkpoints, sentiment
serialization, optional model scoring and missing-data handling.

Imported main's opinion trajectory visualization, its tests and example image,
manual persistence tester and sentiment display in the six-agent tester. Added
matplotlib without dropping ddgs, pydantic or the existing VADER version constraint.
Removed duplicated sentiment fields introduced by the automatic model merge.

The visualization uses the shared conservative analytics rules for raw discussions.
Unknown stances remain unknown, analytics errors propagate, and missing values break
chart lines. It does not substitute emotional sentiment for a stance. Existing
numeric stance data can be plotted directly through plot_opinion_trajectory.
The inherited example PNG is a sample, not validation of football claims.

## Validation

The full suite passed: 216 tests, including chart generation and regression
checks for unknown stances, analytics errors and missing-value gaps. Live model, database and
web calls are outside this merge's offline validation.

Install requirements before using the visualization:

    python -m pip install -r requirements.txt
    python -m src.visualization.opinion_trajectory --input outputs/DISCUSSION_ID.json

A discussion with no classifiable opinions raises an explicit no-plottable-data
error. Supply scored numeric data for such a discussion instead of interpreting
sentiment as agreement.
