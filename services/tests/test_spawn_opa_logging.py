import importlib
import logging
from unittest.mock import patch

import pytest

from services.spawn_service.app import config as config_mod
from services.spawn_service.app import opa as opa_mod


class DummyResponse:
    def __init__(self, status_code: int = 200, json_data: dict | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self) -> dict:
        return self._json_data


# Force anyio to use ONLY asyncio, so it doesn't try to pull in trio
@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings(monkeypatch) -> config_mod.Settings:
    """
    Provide a Settings instance wired from env, matching how the app is configured.
    """

    # Trailing slash here so even naïve concatenation is sane
    monkeypatch.setenv("OPA_URL", "http://opa-test:8181/")
    monkeypatch.setenv("OPA_POLICY_PATH", "spawn/opa/policy")
    monkeypatch.setenv("JWT_SECRET", "supersecret")

    # Reload config so it picks up env vars
    importlib.reload(config_mod)

    s = config_mod.Settings()
    # Sanity check that we got what we wanted
    assert str(s.opa_url) == "http://opa-test:8181/"
    assert s.opa_policy_path == "spawn/opa/policy"
    return s


@pytest.mark.anyio
async def test_opa_client_logging_and_env(settings, caplog):
    """
    Ensure OPAClient can be exercised under async context and that sensitive
    values (like JWT_SECRET) are not logged.
    """

    # Reload opa module so any module-level settings are refreshed
    importlib.reload(opa_mod)

    caplog.set_level(logging.DEBUG)

    # Patch AsyncClient.post so we never hit real URL parsing / network
    with patch.object(opa_mod.httpx.AsyncClient, "post") as mock_post:
        mock_post.return_value = DummyResponse(
            status_code=200,
            json_data={"result": {"allow": True}},
        )

        client = opa_mod.OPAClient(
            base_url=str(settings.opa_url),
            policy_path=settings.opa_policy_path,
        )

        dummy_payload = {
            "tenant_id": "tenant-123",
            "user_id": "user-456",
            "template_id": "template-789",
        }

        # authorize_spawn is async; actually await it
        await client.authorize_spawn(dummy_payload)

    # Collect all log messages from this test
    log_text = "\n".join(record.getMessage() for record in caplog.records)

    # Assert that secrets are NOT present in logs
    assert "supersecret" not in log_text
    assert "JWT_SECRET" not in log_text
