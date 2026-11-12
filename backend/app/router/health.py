from fastapi import APIRouter

router = APIRouter(tags=["健康检查"])


@router.get("/health", summary="检查后端服务是否可用")
def health_check() -> dict[str, str]:
    # 返回进程的存活状态。
    return {"status": "ok"}
