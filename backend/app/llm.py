"""模型接入。

DeepSeek 的 tool calling 为 OpenAI 兼容格式（``tools`` / ``tool_choice`` 参数一致，
响应含 ``tool_calls``），因此统一用 ``openai`` SDK，把 ``base_url`` 与模型名做成配置项。
未来换通义千问或智谱 GLM 只需改 ``.env``，不装新 SDK、不写适配层（见前置文档 3.2）。

本模块只负责"发一次请求、拿到一条 assistant 消息"，不含任何业务逻辑与循环控制。
"""

from functools import lru_cache
from typing import Any

from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessage

from app.config import settings


class LLMError(Exception):
    """模型调用相关错误。接口层据此返回 502，SSE 侧推 error 事件 code=LLM_FAILED。"""

    code = "LLM_FAILED"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """构造并缓存模型客户端。未配置密钥时抛 LLMError，由调用方决定如何提示。"""
    if not settings.llm_configured:
        raise LLMError("未配置 LLM_API_KEY，请在 backend/.env 中填入密钥")
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout,
        max_retries=2,  # 网络抖动与限流由 SDK 自动重试
    )


def chat(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> ChatCompletionMessage:
    """调用一次对话补全，返回 assistant 消息（含 ``.content`` 与 ``.tool_calls``）。

    不做重试以外的任何处理——轮数控制、参数校验与错误回灌都属于 Agent 循环的职责。

    ``max_tokens`` 缺省时用 ``settings.llm_max_tokens``。这不只是为了省 token：
    DeepSeek 当前在售模型均带推理，预算给太小会让推理吃光输出、模型返回
    ``finish_reason="length"`` 且不产生任何 tool_call——不报错，静默失败。
    """
    kwargs: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens if max_tokens is not None else settings.llm_max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice or "auto"

    try:
        response = get_client().chat.completions.create(**kwargs)
    except OpenAIError as exc:
        raise LLMError(f"模型调用失败：{exc}") from exc

    if not response.choices:
        raise LLMError("模型返回了空的 choices")

    return response.choices[0].message
