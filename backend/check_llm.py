"""S1 自检脚本：验证 DeepSeek 连通性与 tool calling 是否可用。

这是本架构最关键的假设——若模型不支持稳定的 function calling，
Agent 循环（S4）与全部工具（S3）都无从谈起，因此必须在 S1 就验证。

用法（工作目录为 backend/）：
    ..\\.venv\\Scripts\\python.exe check_llm.py
"""

import json
import sys

from app.config import settings
from app.llm import LLMError, chat
from app.schemas import JobAnalysis

JD_SAMPLE = """岗位名称：后端开发实习生
岗位职责：
1. 负责后端服务的设计与开发，参与高并发场景下的性能优化
2. 独立负责模块开发
任职要求：
1. 熟悉 Java、Spring Boot、MySQL，了解 Redis 缓存
2. 每周到岗 4 天以上，可连续实习 6 个月
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "emit_job_analysis",
            "description": "输出岗位需求的结构化分析结果",
            "parameters": JobAnalysis.model_json_schema(),
        },
    }
]


def check_plain_chat() -> bool:
    print("[1/2] 普通对话调用")
    try:
        message = chat(
            [
                {"role": "system", "content": "你是简历优化助手，回答务必简短。"},
                {"role": "user", "content": "用一句话说明简历与岗位不匹配最常见的三个原因。"},
            ],
            temperature=0.3,
        )
    except LLMError as exc:
        print(f"  [FAIL] {exc}")
        return False
    print(f"  模型回复：{(message.content or '').strip()[:120]}")
    print("  [OK]")
    return True


def check_tool_calling() -> bool:
    print()
    print("[2/2] tool calling（本架构的核心假设）")
    try:
        message = chat(
            [
                {"role": "system", "content": "你是岗位分析助手，必须调用工具输出结构化结果。"},
                {"role": "user", "content": f"分析这个岗位：\n\n{JD_SAMPLE}"},
            ],
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1,
        )
    except LLMError as exc:
        print(f"  [FAIL] {exc}")
        return False

    if not message.tool_calls:
        print("  [FAIL] 模型没有返回 tool_calls，工具调用不可用")
        print(f"  实际返回：{(message.content or '')[:200]}")
        return False

    call = message.tool_calls[0]
    print(f"  调用工具：{call.function.name}")
    try:
        parsed = JobAnalysis.model_validate_json(call.function.arguments)
    except Exception as exc:  # noqa: BLE001 - 自检脚本，需要看到任何校验异常
        print(f"  [FAIL] 工具参数未通过 Pydantic 校验：{exc}")
        print(f"  原始参数：{call.function.arguments[:300]}")
        return False

    print("  参数通过 Pydantic 校验，解析结果：")
    print(json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2))
    print("  [OK]")
    return True


def main() -> int:
    if not settings.llm_configured:
        print("未配置 LLM_API_KEY。")
        print("请在 backend/.env 中填入密钥后重试（该文件不入仓库）。")
        return 1

    print(f"base_url : {settings.llm_base_url}")
    print(f"model    : {settings.llm_model}")
    print()

    plain_ok = check_plain_chat()
    tool_ok = check_tool_calling()

    print()
    if plain_ok and tool_ok:
        print("S1 自检通过：模型连通，tool calling 可用。")
        return 0
    print("S1 自检未通过，先解决上面的 FAIL 再继续 S2。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
