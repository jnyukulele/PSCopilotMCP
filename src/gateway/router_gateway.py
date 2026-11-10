"""
【50名規模運用向け】社内センターゲートウェイ (オプション)
M365 Copilot の宣言型エージェントは 1つの HTTPS エンドポイント URL を参照します。
50名全員に同じ M365 エージェントを配布しつつ、各ユーザーのローカルPC (オンデマンド起動中の EXE :8765) へ
リクエストを振り分けるための軽量 FastAPI リバースプロキシの雛形です。
"""
import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response

app = FastAPI(title="Photoshop MCP 50-User Department Gateway")

# 実運用では Entra ID のユーザー名 または 社内DNS (例: PC-{username}.corp.local:8765) に解決します
USER_WORKSTATION_MAP = {
    "user01@example.com": "http://PC-USER01.corp.local:8765",
    "user02@example.com": "http://PC-USER02.corp.local:8765",
}


@app.api_route("/mcp/{path:path}", methods=["GET", "POST", "DELETE"])
@app.api_route("/mcp", methods=["GET", "POST", "DELETE"])
async def proxy_to_user_pc(
    request: Request,
    x_Target_Workstation: str = Header(default=""),
):
    """
    M365 Copilot からの MCP Streamable HTTP 通信を受け取り、
    対象ユーザーのオンデマンド起動中PC (`http://<PCホスト名>:8765/mcp`) へ転送します。
    """
    target_host = x_Target_Workstation or "http://127.0.0.1:8765"
    target_url = f"{target_host.rstrip('/')}/mcp"

    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
                params=request.query_params,
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "手元のPCで『Photoshop × M365 Copilot 連携 (ps-mcp-agent.exe)』が起動していません。"
                "デスクトップのアイコンをダブルクリックして起動してから再度お試しください。"
            ),
        ) from exc
