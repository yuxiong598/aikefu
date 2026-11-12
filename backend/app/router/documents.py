from pathlib import PureWindowsPath
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import staff_user
from ..schema.document import (
    ChunkPreview,
    ChunkPreviewRequest,
    ChunkPreviewResponse,
    ConfirmDocumentRequest,
    ConfirmDocumentResponse,
    DocumentDetail,
    DocumentPreview,
    DocumentSummary,
)
from ..service.document import DocumentParseError, extract_docx_text, extract_pdf_text
from ..service.knowledge import (
    ConfirmationConflict,
    DocumentDeleting,
    DocumentNotFound,
    KnowledgeDeletionError,
    KnowledgeIndexError,
    confirm_document,
    delete_document,
    list_documents,
    read_document,
    retry_document,
)
from ..service.text_splitter import split_text

router = APIRouter(prefix="/documents", tags=["知识库文档"], dependencies=[Depends(staff_user)])
MAX_FILE_SIZE = 10 * 1024 * 1024
TEXT_EXTRACTORS = {".pdf": extract_pdf_text, ".docx": extract_docx_text}


@router.post("/preview", summary="上传文档并预览解析文本")
def preview_document(file: UploadFile) -> DocumentPreview:
    # 只保留文件名，兼容上传方传入的 Windows 或 Unix 路径。
    filename = PureWindowsPath(file.filename or "").name
    extractor = TEXT_EXTRACTORS.get(PureWindowsPath(filename).suffix.lower())
    if extractor is None:
        raise HTTPException(status_code=415, detail="仅支持 .pdf 和 .docx 文件。")

    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="单个文件不得超过 10 MiB。")

    try:
        # 普通 def 路由直接读取同步文件对象，解析结果只用于预览。
        text = extractor(file.file)
    except DocumentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not text:
        raise HTTPException(
            status_code=422,
            detail="文档没有可提取的文字。扫描版 PDF 请先进行 OCR。",
        )

    return DocumentPreview(filename=filename, text=text)


@router.post("/chunks/preview", summary="预览人工编辑后的正文切分")
def preview_chunks(request: ChunkPreviewRequest) -> ChunkPreviewResponse:
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="请输入需要切分的正文。")

    # 只生成待确认的预览，序号与原文中的出现顺序一致。
    return ChunkPreviewResponse(
        chunks=[
            ChunkPreview(index=index, text=text)
            for index, text in enumerate(split_text(request.text), start=1)
        ]
    )


@router.post(
    "/confirm",
    summary="确认文档片段并入库",
    responses={
        409: {"description": "同一请求编号已用于不同内容"},
        503: {"description": "正文已保存，向量索引可用原请求重试"},
    },
)
def confirm_document_chunks(
    request: ConfirmDocumentRequest, session: Annotated[Session, Depends(get_db)]
) -> ConfirmDocumentResponse:
    try:
        document_id = confirm_document(
            session, str(request.request_id), request.filename, request.chunks
        )
    except ConfirmationConflict as exc:
        raise HTTPException(status_code=409, detail="该请求编号已用于不同的文档内容。") from exc
    except DocumentDeleting as exc:
        raise HTTPException(status_code=409, detail="该文档正在删除或已删除。") from exc
    except KnowledgeIndexError as exc:
        raise HTTPException(
            status_code=503,
            detail="正文已保存，向量索引未完成。请使用相同请求编号和内容重试。",
        ) from exc

    return ConfirmDocumentResponse(document_id=document_id, chunk_count=len(request.chunks))


DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", summary="查看知识库文档列表")
def documents(session: DatabaseSession) -> list[DocumentSummary]:
    return list_documents(session)


@router.get("/{request_id}", summary="查看文档及片段")
def document(request_id: UUID, session: DatabaseSession) -> DocumentDetail:
    try:
        return read_document(session, str(request_id))
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail="文档不存在。") from exc


@router.post("/{request_id}/retry", summary="重试文档索引")
def retry(request_id: UUID, session: DatabaseSession) -> DocumentDetail:
    try:
        return retry_document(session, str(request_id))
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail="文档不存在。") from exc
    except DocumentDeleting as exc:
        raise HTTPException(status_code=409, detail="文档正在删除。") from exc
    except KnowledgeIndexError as exc:
        raise HTTPException(status_code=503, detail="向量索引未完成，请稍后重试。") from exc


@router.delete("/{request_id}", status_code=204, summary="删除文档、片段和向量")
def delete(request_id: UUID, session: DatabaseSession) -> None:
    try:
        delete_document(session, str(request_id))
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail="文档不存在。") from exc
    except KnowledgeDeletionError as exc:
        raise HTTPException(status_code=503, detail="向量清理未完成，请继续删除。") from exc
