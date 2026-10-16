"""FastAPI 入口。

当前挂三类路由：
- ``/api/health``   配置自检，不调用模型，可安全用于探活
- ``/api/upload``   .docx 简历解析（S2）
- ``/api/sessions`` mock 路由，返回固定数据，供前端开发者立即开工（见前置文档 7.3）

mock 是临时脚手架：S4 上真实 Agent 循环后由 sessions.py 接管并删除。
S7 再补历史记录与导出。
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import mock, upload
from app.config import settings

app = FastAPI(
    title="AI 简历优化智能体",
    version="0.1.0",
    description="软件工程课程项目。接口契约见仓库根目录《接口文档.md》。",
)

# 开发期前端走 Vite 代理，本不需要 CORS；此处配置是为部署时可直接跨域调用。
# 白名单走 .env，代码中不出现具体地址（前置文档 2.3「可部署」要求）。
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(upload.router)
app.include_router(mock.router)


@app.get("/api/health", tags=["运维"])
async def health() -> dict:
    """自检：回报当前配置，不发起模型调用。"""
    return {
        "status": "ok",
        "llm": {
            "model": settings.llm_model,
            "base_url": settings.llm_base_url,
            "api_key_configured": settings.llm_configured,
        },
        "limits": {
            "max_tool_turns": settings.max_tool_turns,
            "max_questions": settings.max_questions,
        },
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
