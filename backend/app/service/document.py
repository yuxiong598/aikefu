from typing import BinaryIO
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.exceptions import InvalidXmlError
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml.etree import XMLSyntaxError
from pypdf import PdfReader
from pypdf.errors import PyPdfError


class DocumentParseError(ValueError):
    """携带可向用户展示的文档解析错误。"""


def extract_pdf_text(stream: BinaryIO) -> str:
    """按页提取 PDF 的文字层。"""
    try:
        reader = PdfReader(stream)
        if not reader.is_encrypted:
            return "\n\n".join(
                text for page in reader.pages if (text := page.extract_text().strip())
            )
    except PyPdfError as exc:
        raise DocumentParseError("PDF 文件损坏或格式无效。") from exc

    raise DocumentParseError("请先解除 PDF 加密，再上传预览。")


def extract_docx_text(stream: BinaryIO) -> str:
    """按正文顺序提取 Word 段落和表格文字。"""
    try:
        document = Document(stream)
        parts: list[str] = []
        for block in document.iter_inner_content():
            if isinstance(block, Paragraph):
                parts.append(block.text.strip())
            elif isinstance(block, Table):
                # 每行表格保留为一行文本，用制表符区分单元格。
                for row in block.rows:
                    parts.append("\t".join(cell.text.strip() for cell in row.cells).strip())
    except (
        BadZipFile,
        InvalidXmlError,
        KeyError,
        PackageNotFoundError,
        ValueError,
        XMLSyntaxError,
    ) as exc:
        raise DocumentParseError("Word 文件损坏或格式无效。") from exc

    return "\n".join(part for part in parts if part)
