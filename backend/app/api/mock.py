"""S1 假数据接口。

让前端不必等 S2–S5 的真实链路就能开发全部界面与交互（见《项目前置文档》7.3）。

**本模块是临时脚手架。** S4 实现真实 Agent 循环后由 sessions.py 接管这些路径，
届时整个模块删除。因此这里不做持久化、不接模型、不追求容错，
只保证一件事：**事件序列与《接口文档》第五节完全一致**。

包含一次完整的多轮问答（question 事件后挂起，等 /reply 再恢复），
既是前端开发提问交互所需，也是 S5 挂起/恢复机制的早期原型。
"""

import asyncio
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.api import mock_data
from app.schemas import AskUserArgs, SessionState

router = APIRouter(prefix="/api", tags=["mock（S1 脚手架）"])


def _now() -> datetime:
    return datetime.now().astimezone()


def _preview(text: str, limit: int = 50) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + "…"


@dataclass
class MockSession:
    session_id: str
    resume_text: str
    jd_text: str
    created_at: datetime
    updated_at: datetime
    state: SessionState = SessionState.created
    pending_question: AskUserArgs | None = None
    answer: str | None = None
    question_count: int = 0
    # 挂起/恢复：await 这个事件，/reply 时 set()。S5 的真实实现同此思路
    reply_event: asyncio.Event = field(default_factory=asyncio.Event)


_sessions: dict[str, MockSession] = {}


class CreateSessionRequest(BaseModel):
    resume_text: str
    jd_text: str


class ReplyRequest(BaseModel):
    question_id: str
    answer: str


def _get(session_id: str) -> MockSession:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


# ── 接口 ────────────────────────────────────────


@router.post("/sessions", status_code=201)
async def create_session(payload: CreateSessionRequest) -> dict:
    """创建会话。S1 不接模型，只登记会话并返回 id。"""
    now = _now()
    session = MockSession(
        session_id=f"s_{secrets.token_hex(6)}",
        resume_text=payload.resume_text,
        jd_text=payload.jd_text,
        created_at=now,
        updated_at=now,
    )
    _sessions[session.session_id] = session
    return {
        "session_id": session.session_id,
        "state": session.state.value,
        "created_at": now.isoformat(),
    }


@router.get("/sessions/{session_id}/stream")
async def stream(session_id: str) -> EventSourceResponse:
    """订阅分析事件流（脚本化回放）。收到 done 或 error 后前端须 es.close()。"""
    return EventSourceResponse(_script(_get(session_id)))


@router.post("/sessions/{session_id}/reply")
async def reply(session_id: str, payload: ReplyRequest) -> dict:
    """回答 Agent 的提问，唤醒挂起的循环。"""
    session = _get(session_id)
    if session.state is not SessionState.awaiting_user:
        raise HTTPException(status_code=400, detail="当前没有待回答的问题")
    if session.pending_question is None or payload.question_id != session.pending_question.question_id:
        raise HTTPException(status_code=400, detail="question_id 不匹配")
    answer = payload.answer.strip()
    if not answer:
        raise HTTPException(status_code=400, detail="回答不能为空")

    session.answer = answer
    session.state = SessionState.running
    session.updated_at = _now()
    session.reply_event.set()
    return {"ok": True, "state": session.state.value}


@router.get("/sessions")
async def list_sessions() -> dict:
    """历史记录列表。列表不返回简历正文，避免响应过大。"""
    items = [
        {
            "session_id": s.session_id,
            "state": s.state.value,
            "resume_preview": _preview(s.resume_text),
            "jd_preview": _preview(s.jd_text),
            "score": mock_data.MOCK_REPORT.score if s.state is SessionState.done else None,
            "question_count": s.question_count,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sorted(_sessions.values(), key=lambda s: s.updated_at, reverse=True)
    ]
    return {"total": len(items), "items": items}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    """历史记录详情。"""
    s = _get(session_id)
    return {
        "session_id": s.session_id,
        "state": s.state.value,
        "resume_text": s.resume_text,
        "jd_text": s.jd_text,
        "turns": [],
        "pending_question": s.pending_question.model_dump() if s.pending_question else None,
        "question_count": s.question_count,
        "report": mock_data.MOCK_REPORT.model_dump() if s.state is SessionState.done else None,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    """删除记录（隐私要求，前端须二次确认）。"""
    _get(session_id)
    del _sessions[session_id]
    return {"ok": True}


# ── 脚本化事件回放 ──────────────────────────────


def _event(name: str, data: dict) -> dict:
    return {"event": name, "data": json.dumps(data, ensure_ascii=False)}


async def _script(session: MockSession):
    """按固定剧本回放一次完整分析。

    重连会从头重放——S1 脚手架不做事件去重，前端据此调样式即可。
    """

    def step(name: str, message: str) -> dict:
        return _event("agent_step", {"step": name, "message": message})

    session.state = SessionState.running
    yield _event("session", {"session_id": session.session_id, "state": session.state.value})

    # —— F2 岗位需求分析 ——
    yield step("parse_jd", "正在分析岗位需求…")
    yield _event("tool_call", {"tool": "analyze_job_description", "args_summary": f"JD 文本 {len(session.jd_text)} 字"})
    await asyncio.sleep(0.4)
    yield _event("tool_result", {"tool": "analyze_job_description", "summary": mock_data.MOCK_TOOL_SUMMARIES["analyze_job_description"]})

    # —— F3 简历内容分析 ——
    yield step("parse_resume", "正在分析简历内容…")
    yield _event("tool_call", {"tool": "analyze_resume", "args_summary": f"简历文本 {len(session.resume_text)} 字"})
    await asyncio.sleep(0.4)
    yield _event("tool_result", {"tool": "analyze_resume", "summary": mock_data.MOCK_TOOL_SUMMARIES["analyze_resume"]})

    # —— D6 多轮问答：挂起等待用户回答（S5 的真实机制与此相同）——
    if session.answer is None:
        session.pending_question = AskUserArgs(**mock_data.MOCK_QUESTION)
        session.question_count = 1
        session.state = SessionState.awaiting_user
        session.updated_at = _now()
        yield _event("tool_call", {"tool": "ask_user", "args_summary": "信息不足，向用户提问"})
        yield _event("question", session.pending_question.model_dump())
        await session.reply_event.wait()

    session.state = SessionState.running
    yield _event("tool_result", {"tool": "ask_user", "summary": f"用户补充：{session.answer}"})

    # —— F4 匹配度评估与建议生成 ——
    yield step("match", "正在评估匹配度并生成建议…")
    yield _event("tool_call", {"tool": "match_and_suggest", "args_summary": "简历分析 + 岗位要求 + 用户补充"})
    await asyncio.sleep(0.4)
    yield _event("tool_result", {"tool": "match_and_suggest", "summary": mock_data.MOCK_TOOL_SUMMARIES["match_and_suggest"]})

    session.state = SessionState.done
    session.pending_question = None
    session.updated_at = _now()
    yield _event("done", {"session_id": session.session_id, "report": mock_data.MOCK_REPORT.model_dump()})
