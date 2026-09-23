"""Week 4 — Reusable Discussion Analytics Engine.

Consumes Week 3 discussion history (DiscussionResult, dictionary, or JSON file)
and computes all required analytics categories:
1. Per-agent opinion change across rounds.
2. Per-round agreement/disagreement.
3. Per-agent influence scores (correlation & distance reduction).
4. Per-message sentiment scores.
5. Unified analytics result containing all of the above.
6. Automatically generated human-readable Markdown report.
7. Opinion trajectory visualization.
8. Weighted interaction graph visualization.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AnalyticsEngine:
    """Reusable analytics engine consuming Week 3 discussion history.

    Examples
    --------
    >>> from src.analytics import AnalyticsEngine
    >>> from src.discussion.persistence import load_discussion
    >>>
    >>> engine = AnalyticsEngine(reports_dir="reports")
    >>> discussion = load_discussion("outputs/discussion.json")
    >>> result = engine.analyze(discussion, generate_charts=True, generate_report=True)
    >>> print(result["discussion_id"], result["metadata"]["scoring_method"])
    """

    def __init__(self, reports_dir: str | Path = "reports") -> None:
        self.reports_dir = str(reports_dir)

    def analyze(
        self,
        discussion: Any,
        *,
        output_path: str | Path | None = None,
        use_llm: bool = False,
        use_embeddings: bool = False,
        positive_pole: str | None = None,
        negative_pole: str | None = None,
        scores_from: Any | None = None,
        generate_charts: bool = False,
        generate_report: bool = False,
        reports_dir: str | Path | None = None,
        counterfactual_ablation: bool = False,
        key_insights: bool = False
    ) -> dict[str, Any]:
        """Compute all 4 analytics categories and optionally generate charts & reports.

        Parameters
        ----------
        discussion : DiscussionResult, dict, or str/Path
            The Week 3 discussion data or path to saved discussion JSON.
        output_path : str or Path, optional
            Where to persist the unified analytics JSON.
        use_llm : bool, default False
            Whether to use LLM for semantic stance scoring.
        use_embeddings : bool, default False
            Whether to use local sentence embeddings for stance scoring.
        positive_pole : str, optional
            Explicit thesis statement representing +1.0 stance.
        negative_pole : str, optional
            Explicit antithesis statement representing -1.0 stance.
        scores_from : str, Path, or dict, optional
            Precomputed analytics JSON or dict to reuse stance scores without model calls.
        generate_charts : bool, default False
            Whether to generate opinion trajectory and interaction graph visualizations.
        generate_report : bool, default False
            Whether to generate an automated Markdown report.
        reports_dir : str or Path, optional
            Directory to store generated visualizations and reports.
        counterfactual_ablation : bool, default False
            Whether to run LLM counterfactual ablation to evaluate causal influence.

        Returns
        -------
        dict[str, Any]
            Unified analytics dictionary containing task1 through task4 results,
            metadata, and optional visualization/report file paths.
        """
        target_reports_dir = reports_dir or self.reports_dir
        from src.analytics.run_analytics import run_analytics_pipeline

        return run_analytics_pipeline(
            discussion,
            use_llm=use_llm,
            output_path=output_path,
            use_embeddings=use_embeddings,
            positive_pole=positive_pole,
            negative_pole=negative_pole,
            scores_from=scores_from,
            generate_charts=generate_charts,
            generate_report=generate_report,
            reports_dir=str(target_reports_dir),
            counterfactual_ablation=counterfactual_ablation,
            key_insights=key_insights,
        )
