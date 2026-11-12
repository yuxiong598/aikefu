import re

MAX_CHUNK_LENGTH = 500
PARAGRAPH_END = re.compile(r"(?:\r\n|[\r\n\u2029])+")
SENTENCE_END = re.compile(r"[。！？!?…]+[”’」』）)】]*|\.(?=\s)")


def split_text(text: str) -> list[str]:
    """按原文顺序切分，保留每个字符。"""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHUNK_LENGTH, len(text))
        if end < len(text):
            # 优先使用窗口内最后一个段落边界，其次使用句末边界。
            for pattern in (PARAGRAPH_END, SENTENCE_END):
                boundary = max(
                    (match.end() for match in pattern.finditer(text, start, end)),
                    default=start,
                )
                if boundary > start:
                    end = boundary
                    break

        # 窗口内没有边界时按长度切开，避免超长句超过限制。
        chunks.append(text[start:end])
        start = end

    return chunks
