"""配置读取。

全部可调项集中在 ``backend/.env``，代码中不出现地址、端口、密钥字面量——
这是《项目前置文档》2.3「可部署」要求的落实：未来部署到服务器只改 .env。

API Key 由后端统一持有，用户无需自备（11.2 的 O1 决策）。前端不得接触任何密钥。
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

# .env 由 .gitignore 排除，不入仓库；提交时附带 .env.example 供他人照填
load_dotenv(BACKEND_DIR / ".env")


def _env_str(key: str, default: str = "") -> str:
    raw = os.getenv(key)
    return raw.strip() if raw and raw.strip() else default


def _env_int(key: str, default: int) -> int:
    raw = _env_str(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"环境变量 {key} 需为整数，当前为 {raw!r}") from None


def _env_float(key: str, default: float) -> float:
    raw = _env_str(key)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"环境变量 {key} 需为数字，当前为 {raw!r}") from None


def _env_list(key: str, default: tuple[str, ...] = ()) -> list[str]:
    raw = _env_str(key)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # ── 模型 ────────────────────────────────────
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout: float
    llm_max_tokens: int

    # ── 服务 ────────────────────────────────────
    host: str
    port: int
    cors_origins: list[str]

    # ── 存储 ────────────────────────────────────
    data_dir: Path

    # ── 循环上限（S4/S5 使用，见前置文档 4.2 / 4.3）──
    max_tool_turns: int
    max_questions: int
    session_timeout_minutes: int

    @property
    def llm_configured(self) -> bool:
        """是否已配置 API Key。未配置时应用仍可启动，仅真实模型调用不可用。"""
        return bool(self.llm_api_key)


settings = Settings(
    llm_base_url=_env_str("LLM_BASE_URL", "https://api.deepseek.com"),
    llm_api_key=_env_str("LLM_API_KEY"),
    # 当前 DeepSeek 在售 deepseek-flash 与 deepseek-v4-pro，均为带推理的模型
    llm_model=_env_str("LLM_MODEL", "deepseek-flash"),
    llm_timeout=_env_float("LLM_TIMEOUT_SECONDS", 60.0),
    # 推理 token 计入输出。给太小，推理会吃光预算，模型返回 finish_reason=length
    # 且不调用任何工具——静默失败，故默认给足（见前置文档 3.2 实测记录）
    llm_max_tokens=_env_int("LLM_MAX_TOKENS", 8000),
    host=_env_str("APP_HOST", "127.0.0.1"),
    port=_env_int("APP_PORT", 8000),
    cors_origins=_env_list(
        "CORS_ORIGINS",
        ("http://localhost:5173", "http://127.0.0.1:5173"),
    ),
    data_dir=Path(_env_str("DATA_DIR") or BACKEND_DIR / "data"),
    max_tool_turns=_env_int("MAX_TOOL_TURNS", 12),
    max_questions=_env_int("MAX_QUESTIONS", 5),
    session_timeout_minutes=_env_int("SESSION_TIMEOUT_MINUTES", 30),
)
