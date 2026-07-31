from packages.config_core.loader import ModelConfig
from packages.llm_runtime.adapter import LlamaCppChatAdapter
from packages.llm_runtime.schemas import ChatCompletionRequest, ChatMessage, RequestMetadata


def test_build_payload_overrides_model_and_drops_metadata() -> None:
    adapter = LlamaCppChatAdapter()
    model_config = ModelConfig(
        provider="llama_cpp",
        model="qwen3-8b",
        base_url="http://localhost:8081/v1",
        default_temperature=0.7,
    )
    request = ChatCompletionRequest(
        model="auto",
        messages=[ChatMessage(role="user", content="hello")],
        metadata=RequestMetadata(mode="fast"),
    )

    payload = adapter._build_payload(model_config=model_config, request_payload=request)

    assert payload["model"] == "qwen3-8b"
    assert payload["temperature"] == 0.7
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert "metadata" not in payload


def test_build_payload_preserves_thinking_for_non_fast_modes() -> None:
    adapter = LlamaCppChatAdapter()
    model_config = ModelConfig(
        provider="llama_cpp",
        model="qwen3-30b",
        base_url="http://localhost:8082/v1",
    )
    request = ChatCompletionRequest(
        model="auto",
        messages=[ChatMessage(role="user", content="analyze this")],
        metadata=RequestMetadata(mode="work"),
    )

    payload = adapter._build_payload(model_config=model_config, request_payload=request)

    assert "chat_template_kwargs" not in payload
