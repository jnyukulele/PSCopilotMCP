"""
PCに詳しくない部署メンバー（約50名）向けの「利用時オンデマンド起動」ランチャー。
- Windows起動時には自動起動せず、使いたい時だけアイコンをダブルクリックして起動します。
- 黒いコマンドプロンプト画面を出さず、小さなステータスウィンドウ（またはタスクトレイ）で
  「M365 Copilot 連携中（停止ボタン付き）」を表示します。
"""
import os
import socket
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import uvicorn
from server import mcp


class OnDemandMcpApp:
    def __init__(self, port: int = 8765) -> None:
        self.port = port
        self.root = tk.Tk()
        self.root.title("Photoshop × M365 Copilot 連携")
        self.root.geometry("380x210")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.hostname = socket.gethostname()
        self.username = os.environ.get("USERNAME", "User")
        self.export_dir = Path.home() / "Pictures" / "Photoshop_MCP_Exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)

        self._build_ui()
        self._start_server_thread()

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=16, pady=14)
        frame.pack(fill=tk.BOTH, expand=True)

        lbl_status = tk.Label(
            frame,
            text="● M365 Copilot 連携稼働中",
            fg="#107C41",
            font=("Meiryo UI", 12, "bold"),
        )
        lbl_status.pack(anchor="w")

        info_text = (
            f"PC名: {self.hostname}  (ユーザー: {self.username})\n"
            f"待受ポート: {self.port} (/mcp)\n"
            "M365 Copilot から Photoshop の画像解析・書き出しが可能です。\n"
            "※使い終わったら下の「連携を終了する」を押してください。"
        )
        lbl_info = tk.Label(frame, text=info_text, justify="left", font=("Meiryo UI", 9))
        lbl_info.pack(anchor="w", pady=(8, 12))

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        btn_open_folder = tk.Button(
            btn_frame,
            text="書き出し先フォルダを開く",
            command=self._open_export_folder,
            font=("Meiryo UI", 9),
            padx=8,
            pady=4,
        )
        btn_open_folder.pack(side=tk.LEFT)

        btn_stop = tk.Button(
            btn_frame,
            text="連携を終了する",
            command=self._shutdown,
            bg="#D83B01",
            fg="white",
            font=("Meiryo UI", 9, "bold"),
            padx=12,
            pady=4,
        )
        btn_stop.pack(side=tk.RIGHT)

        self.root.protocol("WM_DELETE_WINDOW", self._shutdown)

    def _start_server_thread(self) -> None:
        def run_mcp():
            mcp.settings.host = "0.0.0.0"
            mcp.settings.port = self.port
            mcp.run(transport="streamable-http")

        thread = threading.Thread(target=run_mcp, daemon=True)
        thread.start()

    def _open_export_folder(self) -> None:
        os.startfile(str(self.export_dir))

    def _shutdown(self) -> None:
        if messagebox.askokcancel("終了確認", "Photoshop と M365 Copilot の連携を終了しますか？"):
            self.root.destroy()
            os._exit(0)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = OnDemandMcpApp(port=8765)
    app.run()
