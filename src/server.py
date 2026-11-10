"""
Photoshop On-Demand MCP Server (M365 Copilot 対応版)
- Windows COM (`win32com`) 経由でローカルの Photoshop を操作
- M365 Copilot Declarative Agent が要求する「完全フラットなJSONスキーマ（anyOf / Optional 排除）」に準拠
- 利用時のみオンデマンド起動し、Streamable HTTP (デフォルト :8765/mcp) または stdio で待ち受け
"""
import argparse
import json
import os
import socket
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# パス解決（PyInstaller EXE化時および開発時双方に対応）
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = Path(__file__).resolve().parent
for import_path in (ROOT_DIR, SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from ps_com.controller import PhotoshopComError, PhotoshopController

mcp = FastMCP(
    "photoshop-asset-inspector",
    instructions=(
        "ローカルPC上のAdobe PhotoshopをWindows COM経由で自動制御し、"
        "PSDファイル内部のレイヤー構造・画像サイズの解析および指定レイヤーの画像書き出しを行うMCPサーバーです。"
    ),
)

ps_controller = PhotoshopController()


@mcp.tool()
def inspect_psd_structure(
    psd_file_path: str = "",
    include_hidden_layers: bool = False,
) -> str:
    """
    PSDファイル内部の画像・レイヤー一覧、各パーツの座標(x, y)・サイズ(width, height)・表示状態・テキスト内容を解析します。
    psd_file_path を空欄("")にした場合は、現在Photoshopで開いているアクティブなPSDをそのまま解析します。
    """
    try:
        result = ps_controller.open_or_inspect_psd(
            file_path=psd_file_path,
            include_hidden=include_hidden_layers,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except PhotoshopComError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def export_psd_internal_images(
    target_layer_query: str = "*",
    output_folder_path: str = "",
    image_format: str = "PNG",
    trim_transparent_margin: bool = True,
    only_visible_layers: bool = True,
) -> str:
    """
    PSD内部の画像レイヤーを切り出してフォルダへ一括書き出しします。
    - target_layer_query: 書き出したいレイヤー名（部分一致）、レイヤーID、または全レイヤーなら "*" を指定します。
    - output_folder_path: 保存先フォルダパス。空欄("")の場合は「ピクチャ/Photoshop_MCP_Exports」に自動保存されます。
    - image_format: "PNG" または "JPG" を指定します。
    - trim_transparent_margin: Trueにすると各パーツの周囲の透明余白を自動トリミングして実寸で書き出します。
    """
    try:
        result = ps_controller.export_layers_by_query(
            target_query=target_layer_query,
            output_dir=output_folder_path,
            image_format=image_format,
            trim_transparent=trim_transparent_margin,
            only_visible=only_visible_layers,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except PhotoshopComError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def export_psd_full_preview(
    output_file_path: str = "",
    image_format: str = "PNG",
    scale_percent: int = 100,
) -> str:
    """
    現在Photoshopで開いているPSD全体の見た目（統合画像）を1枚の画像ファイル（PNGまたはJPG）として書き出します。
    - output_file_path: 保存先のファイルパス。空欄("")の場合は「ピクチャ/Photoshop_MCP_Exports/document_preview.png」に保存されます。
    - scale_percent: 縮小・拡大率（%）。等倍なら 100、半分なら 50 を指定します。
    """
    try:
        result = ps_controller.export_document_preview(
            output_file_path=output_file_path,
            image_format=image_format,
            scale_percent=scale_percent,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except PhotoshopComError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def get_local_workstation_status() -> str:
    """
    接続中のユーザーPC名（ホスト名）、ログインユーザー名、既定の書き出し先フォルダパスを確認します。
    """
    export_dir = str((Path.home() / "Pictures" / "Photoshop_MCP_Exports").resolve())
    info = {
        "hostname": socket.gethostname(),
        "username": os.environ.get("USERNAME", "unknown"),
        "default_export_directory": export_dir,
        "status": "ready",
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Photoshop COM MCP Server for M365 Copilot")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="streamable-http",
        help="MCP transport type (default: streamable-http)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host for HTTP mode")
    parser.add_argument("--port", type=int, default=8765, help="Bind port for HTTP mode")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
