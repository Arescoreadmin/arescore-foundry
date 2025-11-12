import json

import httpx
import pytest
from fastapi import HTTPException, status

from services.spawn_service.app.opa import OPAClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class DummyResponse:
    def __init__(self, *, status_code: int = 200, payload: dict | None = None, text: str | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)

    def json(self) -> dict:
        return dict(self._payload)


class DummyAsyncClient:
    def __init__(self, *, response: DummyResponse | None = None, exc: Exception | None = None) -> None:
        self._response = response or DummyResponse()
        self._exc = exc
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self) -> "DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401, ANN001
        return None

    async def post(self, url: str, *, json: dict) -> DummyResponse:  # noqa: A003 (shadowing builtins)
        self.calls.append((url, json))
        if self._exc is not None:
            raise self._exc
        return self._response


@pytest.mark.anyio
async def test_authorize_spawn_no_base_url_skips_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_async_client(*args, **kwargs):  # noqa: ANN001, ARG001
        raise AssertionError("AsyncClient should not be constructed when base_url is empty")

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = OPAClient(base_url="", policy_path="/v1/data/spawn/allow")
    await client.authorize_spawn({"demo": True})


@pytest.mark.anyio
async def test_authorize_spawn_allows_when_policy_approves(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_response = DummyResponse(payload={"result": {"allow": True}})
    dummy_client = DummyAsyncClient(response=dummy_response)

    def fake_async_client(*args, **kwargs):  # noqa: ANN001, ARG001
        return dummy_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    payload = {"tenant": {"id": "t-1"}}
    client = OPAClient(base_url="http://opa:8181", policy_path="/v1/data/spawn/allow")

    await client.authorize_spawn(payload)

    assert dummy_client.calls == [
        ("http://opa:8181/v1/data/spawn/allow", {"input": payload}),
    ]


@pytest.mark.anyio
async def test_authorize_spawn_handles_relative_policy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_response = DummyResponse(payload={"result": {"allow": True}})
    dummy_client = DummyAsyncClient(response=dummy_response)

    def fake_async_client(*args, **kwargs):  # noqa: ANN001, ARG001
        return dummy_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    payload = {"tenant": {"id": "t-1"}}
    client = OPAClient(base_url="http://opa:8181/", policy_path="spawn/opa/policy")

    await client.authorize_spawn(payload)

    assert dummy_client.calls == [
        ("http://opa:8181/spawn/opa/policy", {"input": payload}),
    ]


@pytest.mark.anyio
async def test_authorize_spawn_raises_forbidden_with_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_response = DummyResponse(payload={"result": {"allow": False, "reason": "quota exceeded"}})
    dummy_client = DummyAsyncClient(response=dummy_response)

    def fake_async_client(*args, **kwargs):  # noqa: ANN001, ARG001
        return dummy_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = OPAClient(base_url="http://opa:8181", policy_path="/v1/data/spawn/allow")

    with pytest.raises(HTTPException) as excinfo:
        await client.authorize_spawn({"tenant": {"id": "t-1"}})

    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
    assert excinfo.value.detail == "quota exceeded"


@pytest.mark.anyio
async def test_authorize_spawn_raises_forbidden_without_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_response = DummyResponse(payload={"result": False})
    dummy_client = DummyAsyncClient(response=dummy_response)

    def fake_async_client(*args, **kwargs):  # noqa: ANN001, ARG001
        return dummy_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = OPAClient(base_url="http://opa:8181", policy_path="/v1/data/spawn/allow")

    with pytest.raises(HTTPException) as excinfo:
        await client.authorize_spawn({"tenant": {"id": "t-1"}})

    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
    assert excinfo.value.detail == "OPA rejected spawn request"


@pytest.mark.anyio
async def test_authorize_spawn_translates_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_client = DummyAsyncClient(exc=httpx.HTTPError("boom"))

    def fake_async_client(*args, **kwargs):  # noqa: ANN001, ARG001
        return dummy_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = OPAClient(base_url="http://opa:8181", policy_path="/v1/data/spawn/allow")

    with pytest.raises(HTTPException) as excinfo:
        await client.authorize_spawn({})

    assert excinfo.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "OPA request failed" in excinfo.value.detail


@pytest.mark.anyio
async def test_authorize_spawn_surfaces_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_response = DummyResponse(status_code=500, text="internal")
    dummy_client = DummyAsyncClient(response=dummy_response)

    def fake_async_client(*args, **kwargs):  # noqa: ANN001, ARG001
        return dummy_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = OPAClient(base_url="http://opa:8181", policy_path="/v1/data/spawn/allow")

    with pytest.raises(HTTPException) as excinfo:
        await client.authorize_spawn({})

    assert excinfo.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "OPA responded with 500" in excinfo.value.detail
