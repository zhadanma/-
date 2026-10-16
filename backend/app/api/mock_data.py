"""S1 假数据。

数据取自《接口文档》第六节，目的是让前端不必等真实模型接入即可开发全部界面与交互。

这里用 ``schemas`` 的模型构造而非裸 dict——契约一旦改动，本模块会立刻报错，
避免出现"mock 跑得通、真实链路却不符合契约"的假联调成功。
"""

from app.schemas import MatchReport, Suggestion

MOCK_RESUME_TEXT = """李明
求职意向：后端开发实习生
电话：138****0000    邮箱：liming@example.com

教育背景：某某大学 计算机科学与技术 本科 2022.09-2026.06
实习经历：某公司 后端开发 2025.07-2025.09
项目经历：订单系统：负责订单模块开发，使用 Spring Boot + MySQL。
技能：Java、MySQL、Git、Linux
"""

MOCK_JD_TEXT = """岗位名称：后端开发实习生

岗位职责：
1. 负责后端服务的设计与开发，参与高并发场景下的性能优化
2. 独立负责模块开发，编写接口文档与单元测试
3. 与前端协作完成接口联调

任职要求：
1. 熟悉 Java、Spring Boot、MySQL，了解 Redis 缓存
2. 每周到岗 4 天以上，可连续实习 6 个月
3. 有完整的项目经历，能说明自己在项目中承担的具体职责
"""

MOCK_REPORT = MatchReport(
    score=72,
    sub_scores={
        "keyword_coverage": 68,
        "experience_years": 85,
        "skill_match": 70,
    },
    matched=[
        "掌握 Java 与 Spring Boot，与岗位要求的后端技术栈一致",
        "有 MySQL 使用经验并了解索引优化，满足岗位对数据库的要求",
        "有完整的项目经历，符合岗位对项目经验的要求",
    ],
    gaps=[
        "岗位要求掌握 Redis 缓存，简历中未体现相关经验",
        "岗位强调高并发场景，简历项目未说明请求量级与性能数据",
        "项目经历只写了「做了什么」，缺少成果与量化指标",
    ],
    suggestions=[
        Suggestion(
            category="keyword",
            original="熟悉后端开发相关技术",
            rewritten="熟悉 Java / Spring Boot 后端开发，掌握 MySQL 索引优化与 Redis 缓存应用",
            reason="岗位 JD 明确列出 Java、Spring Boot、MySQL、Redis 四项要求，原表述过于笼统，无法被简历筛选系统与 HR 匹配到关键词",
        ),
        Suggestion(
            category="experience",
            original="负责订单系统的开发工作",
            rewritten="独立负责订单系统后端开发，设计并实现订单创建/查询/取消三个核心接口，支撑日均 5 万笔订单，接口平均响应时间从 320ms 优化至 90ms",
            reason="岗位职责强调「独立负责模块开发」与「性能优化」，原描述未体现职责范围与技术深度，且缺少可验证的量化成果",
        ),
        Suggestion(
            category="skill",
            original="技能：Java、MySQL、Git、Linux",
            rewritten="技能：Java、Spring Boot、MyBatis、MySQL（索引优化、事务）、Redis、Git、Linux",
            reason="补充了岗位明确要求但简历遗漏的 Spring Boot、Redis，并对 MySQL 注明掌握深度，与岗位要求逐项对齐",
        ),
        Suggestion(
            category="summary",
            original="求职意向：后端开发实习生",
            rewritten="求职意向：后端开发实习生 | 熟悉 Java 与 Spring Boot，有订单系统后端开发与性能优化经验，可实习 6 个月以上",
            reason="岗位要求「每周到岗 4 天以上、可连续实习 6 个月」，原摘要未回应这一硬性条件，容易在初筛阶段被排除",
        ),
        Suggestion(
            category="format",
            original="教育背景：某某大学 计算机科学与技术 本科 2022.09-2026.06\n实习经历：某公司 后端开发 2025.07-2025.09",
            rewritten="教育背景\n某某大学 | 计算机科学与技术 | 本科 | 2022.09 – 2026.06\n\n实习经历\n某公司 | 后端开发实习生 | 2025.07 – 2025.09",
            reason="原写法把两段经历挤在一行，HR 快速浏览时难以抓取信息。建议每段经历独立成块、时间右对齐，符合国内简历通行排版",
        ),
    ],
)

#: 供步骤轨迹展示用的工具摘要，与 done 之前的 tool_result 事件对应
MOCK_TOOL_SUMMARIES = {
    "analyze_job_description": "提取到 3 项职责、6 个关键词",
    "analyze_resume": "识别到 1 段实习、1 个项目、1 段教育背景",
    "match_and_suggest": "匹配度 72 分，生成 5 条建议",
}

MOCK_QUESTION = {
    "question_id": "q_1",
    "question": "简历中「订单系统」项目未说明你具体负责哪部分，能否补充？",
    "why": "岗位要求独立负责模块开发，需要确认你的实际职责范围",
    "options": [
        "负责后端接口设计与实现",
        "负责数据库表设计",
        "负责整体架构与协调",
        "仅参与部分编码",
    ],
}
