"""在临时数据库中验证完整业务流程，默认用模型接口替身。"""

import argparse
import hashlib
import io
import json as json_codec
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def worker(directory: Path, live: bool) -> None:
    import httpx
    from docx import Document
    from fastapi.testclient import TestClient
    from sqlalchemy import func, select

    from app import config

    original = config.Settings()
    settings = config.Settings(
        sqlite_path=directory / "business.db",
        chroma_dir=directory / "chroma",
        bge_cache_dir=original.bge_cache_dir,
        deepseek_api_key=original.deepseek_api_key if live else "regression-only-key",
    )
    if live and not original.deepseek_api_key:
        raise RuntimeError("--live 需要先在 backend/.env 配置 DEEPSEEK_API_KEY。")

    # 在导入应用前替换设置，所有业务数据只写入本次临时目录。
    with patch.object(config, "Settings", return_value=settings):
        from app.database import SessionLocal
        from app.main import app
        from app.model.chat import ChatTurn
        from app.model.knowledge import KnowledgeChunk
        from app.model.ticket import Ticket
        from app.model.user import LoginSession
        from app.rag.embedding import encode_query
        from app.schema.user import Credentials
        from app.service.auth import create_account
        from app.service.knowledge import _get_store

    calls = []

    def model_response(url, *, json: dict, headers, timeout):
        evidence = json_codec.loads(json["messages"][-1]["content"])["knowledge"]
        assert evidence and any("十五天" in item["text"] for item in evidence)
        assert json["response_format"] == {"type": "json_object"}
        assert headers["Authorization"] == "Bearer regression-only-key"
        citation = next(item["citation"] for item in evidence if "十五天" in item["text"])
        calls.append(url)
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": json_codec.dumps({
                "answer": "根据知识库规则，签收后十五天内可以申请退货。",
                "citations": [citation],
            }, ensure_ascii=False)}}]},
        )

    provider = nullcontext() if live else patch("app.service.deepseek.httpx.post", side_effect=model_response)
    with TestClient(app) as client, provider:
        def api(method, path, token=None, **kwargs):
            headers = kwargs.pop("headers", {})
            if token:
                headers["Authorization"] = "Bearer " + token
            return client.request(method, "/api" + path, headers=headers, **kwargs)

        assert api("GET", "/health").status_code == 200
        assert api("GET", "/documents").status_code == 401
        password = "Temporary-regression-password"
        with SessionLocal() as session:
            create_account(session, Credentials(username="regression_staff", password=password), role="staff")
        for username in ("regression_customer", "regression_other"):
            assert api("POST", "/auth/register", json={"username": username, "password": password}).status_code == 200

        def login(username):
            result = api("POST", "/auth/login", json={"username": username, "password": password})
            assert result.status_code == 200, result.text
            return result.json()["token"]

        staff = login("regression_staff")
        customer = login("regression_customer")
        other = login("regression_other")
        assert api("GET", "/documents", customer).status_code == 403
        print("PASS 注册、登录与角色限制", flush=True)

        conversation = str(uuid4())
        question = "签收后几天内可以退货？"
        message_path = f"/chat/conversations/{conversation}/messages"
        empty = api("POST", message_path, customer, json={
            "request_id": str(uuid4()), "question": question,
        })
        assert empty.status_code == 200 and empty.json()["sources"] == []

        document = Document()
        document.add_paragraph("商品签收后七天内可以申请退货。")
        document.add_paragraph("退货申请时请提供订单编号。")
        upload = io.BytesIO()
        document.save(upload)
        preview = api("POST", "/documents/preview", staff, files={
            "file": ("regression-policy.docx", upload.getvalue(),
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        })
        assert preview.status_code == 200, preview.text
        edited = preview.json()["text"].replace("七天", "十五天")
        split = api("POST", "/documents/chunks/preview", staff, json={"text": edited})
        assert split.status_code == 200
        chunks = [chunk["text"] for chunk in split.json()["chunks"]]
        assert "".join(chunks) == edited
        document_request = str(uuid4())
        confirmation = {"request_id": document_request, "filename": preview.json()["filename"], "chunks": chunks}
        saved = api("POST", "/documents/confirm", staff, json=confirmation)
        assert saved.status_code == 200, saved.text
        assert api("POST", "/documents/confirm", staff, json=confirmation).json() == saved.json()
        assert api("GET", "/documents", staff).json()[0]["status"] == "indexed"
        print("PASS 上传、人工修改、切分、确认入库与重试", flush=True)

        message = {"request_id": str(uuid4()), "question": question}
        answered = api("POST", message_path, customer, json=message)
        assert answered.status_code == 200, answered.text
        answer = answered.json()
        assert answer["answer"].strip() and answer["sources"]
        assert "十五天" in answer["sources"][0]["text"]
        assert answer["sources"][0]["filename"] == preview.json()["filename"]
        assert api("POST", message_path, customer, json=message).json() == answer
        assert live or len(calls) == 1
        assert len(api("GET", f"/chat/conversations/{conversation}", customer).json()["turns"]) == 2
        assert api("GET", f"/chat/conversations/{conversation}", other).status_code == 404
        print("PASS 回答、引用来源、消息保存与账号隔离", flush=True)

        ticket_payload = {
            "request_id": str(uuid4()), "title": "退货申请跟进",
            "description": "请客服核实退货申请。", "conversation_id": conversation,
        }
        result = api("POST", "/tickets", customer, json=ticket_payload)
        assert result.status_code == 200, result.text
        ticket = result.json()
        assert ticket["conversation_snapshot"][-1]["sources"] == answer["sources"]
        assert api("POST", "/tickets", customer, json=ticket_payload).json() == ticket
        assert api("GET", f"/tickets/{ticket['id']}", other).status_code == 404
        status_path = f"/tickets/{ticket['id']}/status"
        assert api("PATCH", status_path, customer, json={"status": "processing", "version": 1}).status_code == 403
        assert api("PATCH", status_path, staff, json={"status": "processing", "version": 1}).status_code == 200
        assert api("PATCH", status_path, staff, json={"status": "completed", "version": 2}).status_code == 200
        assert api("GET", f"/tickets/{ticket['id']}", customer).json()["status"] == "completed"
        manual = api("POST", "/tickets", customer, json={
            "request_id": str(uuid4()), "title": "人工咨询", "description": "请求客服人工协助。",
        })
        assert manual.status_code == 200 and manual.json()["conversation_snapshot"] == []
        print("PASS 会话建单、手动建单、客服处理与用户查看", flush=True)

        assert api("DELETE", f"/documents/{document_request}", staff).status_code == 204
        assert api("DELETE", f"/documents/{document_request}", staff).status_code == 204
        assert api("GET", "/documents", staff).json() == []
        search = api("POST", "/knowledge/search", customer, json={"query": question})
        assert search.status_code == 200 and search.json() == {"hits": []}
        assert _get_store().search(encode_query(question)) == []
        with SessionLocal() as session:
            assert session.scalar(select(func.count()).select_from(KnowledgeChunk)) == 0
            assert session.scalar(select(func.count()).select_from(ChatTurn)) == 2
            assert session.scalar(select(func.count()).select_from(Ticket)) == 2
            assert session.get(LoginSession, hashlib.sha256(customer.encode()).hexdigest()) is not None
        assert api("POST", "/auth/logout", customer).status_code == 204
        assert api("GET", "/auth/me", customer).status_code == 401
        print("PASS 删除同步、历史保留与退出失效", flush=True)
    print("PASS 完整回归结束。模型模式=" + ("DeepSeek 实网" if live else "接口替身"), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="隔离验证毕业设计的完整业务流程")
    parser.add_argument("--live", action="store_true", help="使用后端 .env 中的 DeepSeek，产生一次模型请求")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        worker(args.worker, args.live)
        return
    if sys.version_info < (3, 12):
        parser.exit(1, "需要 Python 3.12 或更新版本。\n")
    if args.live:
        from app.config import Settings

        if not Settings().deepseek_api_key:
            parser.exit(2, "请先在 backend/.env 配置 DEEPSEEK_API_KEY，再运行 --live。\n")
    # 子进程退出后再清理，确保 Windows 上 Chroma 文件句柄已释放。
    with tempfile.TemporaryDirectory(dir=ROOT, prefix="system-check-") as directory:
        path = Path(directory).resolve()
        if path.parent != ROOT.resolve():
            raise RuntimeError("临时目录不在项目中。")
        command = [sys.executable, "-X", "utf8", "-u", str(Path(__file__).resolve()), "--worker", str(path)]
        if args.live:
            command.append("--live")
        result = subprocess.run(command, cwd=ROOT, timeout=600)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
