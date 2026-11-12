from threading import Lock
from typing import TYPE_CHECKING

from ..config import Settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

BGE_QUERY_PROMPT = "为这个句子生成表示以用于检索相关文章："
_model: "SentenceTransformer | None" = None
_model_lock = Lock()


def _encode(texts: list[str], *, prompt: str) -> list[list[float]]:
    if not texts:
        return []
    if any(not text.strip() for text in texts):
        raise ValueError("待向量化的文本不能为空白。")

    global _model
    # 每个进程只加载一份模型，并串行使用同一模型进行推理。
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            settings = Settings()
            # 首次调用可能下载权重并等待初始化，之后复用内存中的模型。
            _model = SentenceTransformer(
                settings.bge_model_name,
                cache_folder=str(settings.bge_cache_dir),
                device="cpu",
            )

        vectors = _model.encode(
            texts,
            prompt=prompt,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    return vectors.tolist()


def encode_documents(texts: list[str]) -> list[list[float]]:
    """批量生成知识片段向量，保持输入顺序。"""
    return _encode(texts, prompt="")


def encode_query(text: str) -> list[float]:
    """按中文 BGE 的检索用法为查询添加指令。"""
    return _encode([text], prompt=BGE_QUERY_PROMPT)[0]
