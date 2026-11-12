from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class KnowledgeSearchRequest(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    top_k: int = Field(default=5, ge=1, le=20, description="最多返回的片段数量")


class KnowledgeHit(BaseModel):
    document_id: int
    filename: str
    position: int = Field(description="片段在文档中的位置，从 1 开始")
    text: str
    distance: float = Field(description="余弦距离，数值越小越相近")


class KnowledgeSearchResponse(BaseModel):
    hits: list[KnowledgeHit]
