"""
Windows COM (`win32com.client`) 経由で Adobe Photoshop を制御するコントローラー。
Streamable HTTP のマルチスレッド実行でもハングアップしないよう、リクエストごとに
`pythoncom.CoInitialize()` / `CoUninitialize()` を確実に管理します。
"""
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict

from src.ps_com.jsx_templates import (
    JSX_EXPORT_FLATTENED,
    JSX_EXPORT_MATCHING_LAYERS,
    JSX_INSPECT_DOCUMENT,
)


class PhotoshopComError(Exception):
    """Photoshop COM通信時のカスタム例外"""


class PhotoshopController:
    def __init__(self, prog_id: str = "Photoshop.Application") -> None:
        self.prog_id = prog_id

    @contextmanager
    def _com_session(self):
        """
        ワーカースレッド内で安全にCOMオブジェクトを扱うためのコンテキストマネージャ。
        Photoshopが未起動の場合でも `Dispatch` によって自動的にプロセスが立ち上がります。
        """
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise PhotoshopComError(
                "pywin32 がインストールされていません。Windows環境で `pip install pywin32` を実行してください。"
            ) from exc

        pythoncom.CoInitialize()
        try:
            app = win32com.client.Dispatch(self.prog_id)
            yield app
        except Exception as exc:
            raise PhotoshopComError(f"Photoshop COM 接続エラー: {exc}") from exc
        finally:
            pythoncom.CoUninitialize()

    def open_or_inspect_psd(self, file_path: str = "", include_hidden: bool = False) -> Dict[str, Any]:
        """
        PSDファイルを開く（パス指定時）か現在開いているアクティブドキュメントを対象に、
        カンバスサイズ・解像度・内部の全レイヤー構造（座標・サイズ・種別・テキスト内容）を解析して返します。
        """
        with self._com_session() as app:
            if file_path.strip():
                norm_path = str(Path(file_path.strip()).expanduser().resolve())
                if not os.path.exists(norm_path):
                    return {"error": f"指定されたPSDファイルが見つかりません: {norm_path}"}
                app.Open(norm_path)

            script = JSX_INSPECT_DOCUMENT.replace(
                "__INCLUDE_HIDDEN__", "true" if include_hidden else "false"
            )
            raw_json = app.DoJavaScript(script)
            return json.loads(raw_json)

    def export_layers_by_query(
        self,
        target_query: str = "*",
        output_dir: str = "",
        image_format: str = "PNG",
        trim_transparent: bool = True,
        only_visible: bool = True,
    ) -> Dict[str, Any]:
        """
        指定した条件（レイヤー名の部分一致、レイヤーID、または '*' で全可視レイヤー）に一致する
        内部画像レイヤーを解析・切り出し、指定フォルダへ一括書き出しします。
        """
        with self._com_session() as app:
            if not output_dir.strip():
                # 未指定時はユーザーのピクチャ/Photoshop_MCP_Exportsに出力
                default_dir = Path.home() / "Pictures" / "Photoshop_MCP_Exports"
                resolved_out = str(default_dir.resolve())
            else:
                resolved_out = str(Path(output_dir.strip()).expanduser().resolve())

            safe_query = target_query.replace("\\", "\\\\").replace('"', '\\"')
            safe_out = resolved_out.replace("\\", "/")

            script = (
                JSX_EXPORT_MATCHING_LAYERS.replace("__TARGET_QUERY__", safe_query)
                .replace("__OUTPUT_DIR__", safe_out)
                .replace("__FORMAT__", image_format.strip() or "PNG")
                .replace("__TRIM_BOUNDS__", "true" if trim_transparent else "false")
                .replace("__ONLY_VISIBLE__", "true" if only_visible else "false")
            )
            raw_json = app.DoJavaScript(script)
            return json.loads(raw_json)

    def export_document_preview(
        self,
        output_file_path: str = "",
        image_format: str = "PNG",
        scale_percent: int = 100,
    ) -> Dict[str, Any]:
        """
        現在開いているPSDドキュメント全体の統合プレビュー画像を書き出します。
        """
        with self._com_session() as app:
            ext = ".jpg" if image_format.upper() in ("JPG", "JPEG") else ".png"
            if not output_file_path.strip():
                default_file = (
                    Path.home()
                    / "Pictures"
                    / "Photoshop_MCP_Exports"
                    / f"document_preview{ext}"
                )
                resolved_file = str(default_file.resolve())
            else:
                resolved_file = str(Path(output_file_path.strip()).expanduser().resolve())

            safe_file = resolved_file.replace("\\", "/")
            script = (
                JSX_EXPORT_FLATTENED.replace("__OUTPUT_FILE_PATH__", safe_file)
                .replace("__FORMAT__", image_format.strip() or "PNG")
                .replace("__SCALE_PERCENT__", str(max(1, min(scale_percent, 400))))
            )
            raw_json = app.DoJavaScript(script)
            return json.loads(raw_json)
