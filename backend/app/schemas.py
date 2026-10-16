"""全项目共用的 Pydantic 数据契约。

权威定义见《项目前置文档》第六节；面向前端的 TypeScript 版本见《接口文档》第四节。
5 个工具、Agent 循环、接口层与前端都依赖本模块——**改动前必须先同步前端**。

这些模型同时会被转成 JSON Schema 作为工具入参定义（见 S3 的 tools.py），
因此各字段的 description 会直接进入模型提示，需写清语义。
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# ── F2 岗位需求分析 ──────────────────────────────


class JobAnalysis(BaseModel):
    """从 JD 中提取出的岗位要求。"""

    responsibilities: list[str] = Field(description="关键职责")
    required_skills: list[str] = Field(description="硬性技能要求")
    preferred_skills: list[str] = Field(description="加分技能，非硬性要求")
    years_required: str | None = Field(default=None, description="经验年限要求，如「3 年以上」")
    seniority: str | None = Field(default=None, description="职级，如「实习/初级/高级」")
    keywords: list[str] = Field(description="供 ATS 与 HR 快速匹配的核心关键词")


# ── F3 简历内容分析 ──────────────────────────────


class Experience(BaseModel):
    """一段工作或实习经历。"""

    company: str = Field(description="公司名称")
    title: str = Field(description="职位名称")
    period: str = Field(description="起止时间，如「2025.07-2025.09」")
    bullets: list[str] = Field(description="该经历下的职责与成果描述")


class Project(BaseModel):
    """一段项目经历。"""

    name: str = Field(description="项目名称")
    role: str = Field(description="担任角色")
    description: str = Field(description="项目简介")
    highlights: list[str] = Field(description="项目亮点与成果")


class Education(BaseModel):
    """一段教育经历。"""

    school: str = Field(description="学校名称")
    major: str = Field(description="专业")
    degree: str = Field(description="学历，如「本科/硕士」")
    period: str = Field(description="起止时间")


class ResumeAnalysis(BaseModel):
    """简历内容的结构化提取结果。"""

    skills: list[str] = Field(description="技能清单")
    experiences: list[Experience] = Field(description="工作与实习经历")
    projects: list[Project] = Field(description="项目经历")
    education: list[Education] = Field(description="教育背景")


# ── F4 匹配与建议 ────────────────────────────────

SuggestionCategory = Literal[
    "keyword",  # F4-1 关键词建议
    "experience",  # F4-2 经历描述优化
    "skill",  # F4-3 技能匹配
    "summary",  # F4-4 摘要/目标优化
    "format",  # F4-5 格式与表达
]

#: MatchReport.sub_scores 的固定键名，与《接口文档》4.1 节一一对应
SUB_SCORE_KEYS = ("keyword_coverage", "experience_years", "skill_match")


class Suggestion(BaseModel):
    """一条优化建议。

    original 与 rewritten 成对出现，前端左栏放 original、右栏放 rewritten，
    逐条并排高亮即可——「修改前后对照」因此不需要实现 diff 算法。
    """

    category: SuggestionCategory = Field(description="建议所属方向")
    original: str = Field(description="简历原文片段——对照视图左栏")
    rewritten: str = Field(description="建议改写后的内容——对照视图右栏")
    reason: str = Field(description="改写理由，须能追溯到 JD 的具体要求")


class MatchReport(BaseModel):
    """匹配度评估与优化建议，是 done 事件的核心载荷。"""

    score: int = Field(ge=0, le=100, description="匹配度总分 0–100")
    sub_scores: dict[str, int] = Field(description=f"分项得分，固定键：{'/'.join(SUB_SCORE_KEYS)}")
    matched: list[str] = Field(description="匹配点")
    gaps: list[str] = Field(description="差距")
    suggestions: list[Suggestion] = Field(description="五类优化建议")


# ── F5 改写输出 ─────────────────────────────────


class RewrittenSection(BaseModel):
    """改写后简历的一个段落。"""

    section: str = Field(description="段落名，如「摘要/工作经历/技能」")
    original: str = Field(description="原文")
    rewritten: str = Field(description="改写后")
    reason: str = Field(description="改写理由")


class RewrittenResume(BaseModel):
    """改写后的完整简历。"""

    sections: list[RewrittenSection] = Field(description="按段落组织的改写结果")


# ── D6 多轮问答与会话状态 ────────────────────────


class SessionState(str, Enum):
    """会话状态机。仅 5 个状态，保持简单（见前置文档 4.3）。"""

    created = "created"  # 已创建，尚未订阅事件流
    running = "running"  # Agent 循环执行中
    awaiting_user = "awaiting_user"  # 已挂起，等待用户回答
    done = "done"
    failed = "failed"


class AskUserArgs(BaseModel):
    """ask_user 工具的入参，同时也是 SSE question 事件的载荷与会话的挂起记录。

    三处共用一份定义，避免结构漂移（见前置文档第六节设计要点二）。
    """

    question_id: str = Field(description="问题编号，用于校验用户答的是否为当前问题")
    question: str = Field(description="要问用户的问题")
    why: str | None = Field(default=None, description="为什么问这个，用于向用户解释")
    options: list[str] | None = Field(default=None, description="候选答案，前端渲染为按钮以降低输入成本")


class ConversationTurn(BaseModel):
    """对话轨迹中的一条记录。"""

    role: Literal["user", "assistant", "tool"]
    tool_name: str | None = None
    content: str
    created_at: datetime


class Session(BaseModel):
    """一次完整的分析会话。"""

    session_id: str
    state: SessionState
    resume_text: str = Field(description="本地留存，用于回看历史与继续多轮对话")
    jd_text: str
    turns: list[ConversationTurn] = []
    pending_question: AskUserArgs | None = None
    question_count: int = Field(default=0, description="已提问次数，用于 MAX_QUESTIONS 限制")
    report: MatchReport | None = None
    created_at: datetime
    updated_at: datetime
