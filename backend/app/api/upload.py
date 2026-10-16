"""简历文件上传：把 .docx 解析为文本。

返回的文本**必须回显给用户确认或修正后再提交分析**——Word 排版复杂时
（表格、文本框、分栏）解析难免有出入，让用户先过一眼能显著减少错误结论。
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.parsers.docx import DocxParseError, extract_text

router = APIRouter(prefix="/api", tags=["上传"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
_DOC_SAVE_AS_HINT = "这是旧版 .doc 格式，请在 Word 中另存为 .docx 后重试"


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)) -> dict:
    name = (file.filename or "").strip()
    lower = name.lower()

    if lower.endswith(".doc"):
        raise HTTPException(status_code=400, detail=_DOC_SAVE_AS_HINT)
    if not lower.endswith(".docx"):
        raise HTTPException(status_code=400, detail="不支持的文件类型，请上传 .docx 文件")

    # 多读一个字节即可判断超限，避免把超大文件整个读进内存
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件过大，请上传 5 MB 以内的文件")

    # 扩展名可以随便改，这里再按文件头确认一次
    if data.startswith(b"\xd0\xcf\x11\xe0"):
        raise HTTPException(status_code=400, detail=_DOC_SAVE_AS_HINT)
    if not data.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="文件不是有效的 .docx，请确认后重新上传")

    try:
        text, warnings = extract_text(data)
    except DocxParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": name,
        "text": text,
        "char_count": len(text),
        "warnings": warnings,
    }
