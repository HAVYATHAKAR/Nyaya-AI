import pytest

from app.core.config import settings
from app.services.llm_service import LLMService, LLMUnavailable
from pydantic import ValidationError


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {"message": {"content": [{"type": "text", "text": "Model reply"}]}}
            ]
        }


class FakeClient:
    def __init__(self, response, **_kwargs):
        self.response = response
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, *, headers, json):
        self.request = {"url": url, "headers": headers, "json": json}
        return self.response


@pytest.mark.asyncio
async def test_chat_uses_huggingface_chat_completions_and_task_prompt(monkeypatch):
    monkeypatch.setattr(settings, "hf_token", "test-token")
    monkeypatch.setattr(settings, "hf_model", "example/model")
    monkeypatch.setattr(settings, "hf_api_base_url", "https://router.example/v1/")
    client = FakeClient(FakeResponse())
    monkeypatch.setattr("app.services.llm_service.httpx.AsyncClient", lambda **kwargs: client)

    service = LLMService()
    result = await service.chat(
        [{"role": "user", "content": "Analyze this"}],
        context="untrusted reference text",
        system_prompt="Return a structured summary.",
        max_new_tokens=123,
        temperature=0.2,
    )

    assert result == "Model reply"
    assert client.request["url"] == "https://router.example/v1/chat/completions"
    assert client.request["headers"]["Authorization"] == "Bearer test-token"
    payload = client.request["json"]
    assert payload["model"] == "example/model"
    assert payload["max_tokens"] == 123
    assert [message["role"] for message in payload["messages"]] == ["system", "user"]
    assert payload["messages"][0]["content"] == "Return a structured summary."
    assert "untrusted reference text" in payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_chat_requires_token(monkeypatch):
    monkeypatch.setattr(settings, "hf_token", "")
    monkeypatch.setattr(settings, "hf_model", "example/model")
    service = LLMService()

    with pytest.raises(LLMUnavailable):
        await service.chat([{"role": "user", "content": "Hello"}])


def test_production_config_rejects_debug_and_insecure_model_gateway():
    from app.core.config import Settings

    valid_secret = "A5x!K8nQ2vR7mT4pZ9cL1dF6gH3jW0sB"
    with pytest.raises(ValidationError, match="APP_DEBUG"):
        Settings(app_env="production", app_debug=True, jwt_secret=valid_secret)
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(app_env="production", app_debug=False, jwt_secret=valid_secret,
                 hf_api_base_url="http://inference.example/v1")
