import httpx
from pydantic import BaseModel, Field, StrictInt, ValidationError

from ..config import Settings


class DeepSeekUnavailable(Exception):
    """当前无法连接问答模型。"""


class DeepSeekResponseError(Exception):
    """模型请求失败或响应无法解析。"""


class GroundedAnswer(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[StrictInt]


def generate_answer(settings: Settings, messages: list[dict[str, str]]) -> GroundedAnswer:
    if not settings.deepseek_api_key:
        raise DeepSeekUnavailable("后端尚未配置 DeepSeek API Key。")

    try:
        response = httpx.post(
            f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
            json={
                "model": settings.deepseek_model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "thinking": {"type": "disabled"},
                "max_tokens": 1500,
            },
            headers={"Authorization": f"Bearer {settings.deepseek_api_key.get_secret_value()}"},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise DeepSeekResponseError("DeepSeek 请求失败，请稍后重试。") from exc
    except httpx.RequestError as exc:
        raise DeepSeekUnavailable("暂时无法连接 DeepSeek，请稍后重试。") from exc
    except (ValueError, UnicodeError) as exc:
        raise DeepSeekResponseError("DeepSeek 返回了无法解析的响应。") from exc

    try:
        message = payload["choices"][0]["message"]
        result = GroundedAnswer.model_validate_json(message["content"])
    except (KeyError, IndexError, TypeError, ValidationError) as exc:
        raise DeepSeekResponseError("DeepSeek 返回了无法解析的回答。") from exc
    return result
