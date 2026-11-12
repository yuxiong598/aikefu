from datetime import datetime
from pathlib import PureWindowsPath
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator

from ..service.text_splitter import MAX_CHUNK_LENGTH


class DocumentPreview(BaseModel):
    """供用户核对和编辑的文档文本。"""

    filename: str = Field(description="上传文件名")
    text: str = Field(description="从文档中提取的正文")


class ChunkPreviewRequest(BaseModel):
    text: str = Field(description="人工核对或编辑后的正文")


class ChunkPreview(BaseModel):
    index: int = Field(description="片段序号，从 1 开始")
    text: str = Field(description="保留原始空白的片段文本")


class ChunkPreviewResponse(BaseModel):
    chunks: list[ChunkPreview] = Field(description="按原文顺序排列的片段")


ConfirmedChunkText = Annotated[str, StringConstraints(min_length=1, max_length=MAX_CHUNK_LENGTH)]


class ConfirmDocumentRequest(BaseModel):
    request_id: UUID = Field(description="每次新确认生成一个 UUID，同一请求重试时复用")
    filename: str = Field(min_length=1, max_length=255, description="预览接口返回的文件名")
    chunks: list[ConfirmedChunkText] = Field(min_length=1, description="确认后的片段文本，按原文顺序")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, filename: str) -> str:
        path = PureWindowsPath(filename)
        if "\x00" in filename or path.name != filename or path.suffix.lower() not in {".pdf", ".docx"}:
            raise ValueError("请输入 .pdf 或 .docx 文件名。")
        return filename

    @field_validator("chunks")
    @classmethod
    def validate_chunks(cls, chunks: list[str]) -> list[str]:
        # 保留人工确认的空格和换行，同时阻止只有空白的片段入库。
        if any(not text.strip() for text in chunks):
            raise ValueError("片段不能只包含空白字符。")
        return chunks


class ConfirmDocumentResponse(BaseModel):
    document_id: int
    chunk_count: int


class DocumentSummary(BaseModel):
    document_id: int
    request_id: UUID
    filename: str
    created_at: datetime
    chunk_count: int
    status: Literal["pending", "indexed", "deleting"]


class DocumentDetail(DocumentSummary):
    chunks: list[ChunkPreview]
