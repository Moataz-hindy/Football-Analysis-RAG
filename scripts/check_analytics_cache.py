import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.api.services import analytics_service as service
from src.api.services.discussion_service import get_saved_discussion


def run_checks():
    # Copy a real discussion without changing the original.
    discussion_data = get_saved_discussion(
        "japan-influence-demo-01"
    ).to_dict()

    discussion_id = "analytics-cache-check"
    discussion_data["config"]["discussion_id"] = discussion_id

    with TemporaryDirectory() as folder:
        root = Path(folder)
        outputs = root / "outputs"
        reports = root / "reports"
        outputs.mkdir()

        source = outputs / f"{discussion_id}.json"
        source.write_text(
            json.dumps(discussion_data),
            encoding="utf-8",
        )

        # Redirect analytics reads and writes into temporary folders.
        with (
            patch.object(service, "OUTPUTS_DIR", outputs),
            patch.object(service, "REPORTS_DIR", reports),
        ):
            # 1. No cache exists: calculate analytics.
            raw, cached, discussion = service._load_or_compute_analytics(
                discussion_id
            )

            assert cached is False, "First request unexpectedly used a cache."

            response = service._build_analytics_response(
                raw,
                discussion,
                cached=cached,
            )
            assert response.discussion_id == discussion_id
            assert response.opinion_trajectories

            cache_file = (
                reports / "api_cache" / f"{discussion_id}_analytics.json"
            )
            assert cache_file.is_file(), "Analytics were not saved."

            first_hash = raw["metadata"]["source_sha256"]
            assert first_hash == hashlib.sha256(source.read_bytes()).hexdigest()

            print("PASS: fresh analytics computed, validated, and saved")

            # 2. Same discussion: reuse the saved analytics.
            raw_again, cached, _ = service._load_or_compute_analytics(
                discussion_id
            )

            assert cached is True, "Unchanged discussion did not use its cache."
            assert raw_again == raw

            print("PASS: unchanged discussion reuses identical analytics")

            # 3. Update the discussion through an atomic replacement.
            updated_topic = "Updated topic for analytics cache verification"
            discussion_data["config"]["topic"] = updated_topic

            replacement = outputs / "replacement.tmp"
            replacement.write_text(
                json.dumps(discussion_data),
                encoding="utf-8",
            )
            replacement.replace(source)

            updated_raw, cached, updated_discussion = (
                service._load_or_compute_analytics(discussion_id)
            )

            assert cached is False, "Stale analytics were incorrectly reused."
            assert updated_discussion.config.topic == updated_topic
            assert updated_raw["topic"] == updated_topic

            updated_hash = updated_raw["metadata"]["source_sha256"]
            assert updated_hash != first_hash
            assert updated_hash == hashlib.sha256(
                source.read_bytes()
            ).hexdigest()

            print("PASS: changed discussion triggers fresh analytics")

            # 4. The replacement cache should now be reusable.
            _, cached, _ = service._load_or_compute_analytics(
                discussion_id
            )
            assert cached is True

            print("PASS: refreshed analytics are cached")

            # 5. Broken cache JSON should trigger recalculation.
            cache_file.write_text("{invalid JSON", encoding="utf-8")

            repaired_raw, cached, _ = service._load_or_compute_analytics(
                discussion_id
            )

            assert cached is False
            saved = json.loads(cache_file.read_text(encoding="utf-8"))
            assert saved == repaired_raw
            assert saved["metadata"]["source_sha256"] == updated_hash

            print("PASS: malformed cache is rebuilt successfully")

    print("All analytics cache checks passed.")


if __name__ == "__main__":
    run_checks()