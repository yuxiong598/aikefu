from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import current_user
from ..schema.knowledge import KnowledgeSearchRequest, KnowledgeSearchResponse
from ..service.knowledge import search_knowledge

router = APIRouter(prefix="/knowledge", tags=["知识检索"], dependencies=[Depends(current_user)])


@router.post("/search", summary="检索已入库的知识片段")
def search(
    request: KnowledgeSearchRequest, session: Annotated[Session, Depends(get_db)]
) -> KnowledgeSearchResponse:
    return KnowledgeSearchResponse(hits=search_knowledge(session, request.query, request.top_k))
