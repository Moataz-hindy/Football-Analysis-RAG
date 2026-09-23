from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from src.api.main import app
from src.api.services import discussion_service as service


with patch.object(
    service,
    "_execute_discussion",
    return_value=0,
) as fake_runner:
    for attempt in range(2):
        discussion_id = f"lifecycle-test-{uuid4().hex[:8]}"

        with TestClient(app) as client:
            response = client.post(
                "/discussions",
                json={
                    "discussion_id": discussion_id,
                    "topic": "Lifecycle test",
                    "num_rounds": 3,
                },
            )
            assert response.status_code == 202, response.text

        # Exiting TestClient triggers graceful shutdown.
        record = service.get_runtime_status(discussion_id)

        assert record.status == "completed", record
        assert service._worker_state == "closed"

        print(f"PASS: lifecycle {attempt + 1}")

    assert fake_runner.call_count == 2

print("Startup, shutdown, and restart checks passed.")