# Photoshop × M365 Copilot オンデマンド連携ハーネス (50名部署展開・単一EXE版)

PCに詳しくない部署メンバー（約50名）が、**使いたい時だけアイコンをダブルクリックして起動**し、**Microsoft 365 Copilot App** から自分のPCの **Photoshop** 内のPSD画像解析・書き出しを行えるようにするための VS Code + GitHub Copilot 開発用ハーネスです。

---

## ディレクトリ構成

```text
photoshop-mcp-m365-harness/
├── .github/
│   ├── copilot-instructions.md       # GitHub Copilot Agent Mode 用の設計規約（M365スキーマ制約・COMスレッド制御）
│   └── prompts/
│       └── add-mcp-tool.prompt.md    # 新規Photoshopツール追加用のCopilot再利用プロンプト
├── .vscode/
│   ├── mcp.json                      # VS Code GitHub Copilot Agent Mode でのローカル検証設定
│   ├── tasks.json                    # ワンクリック環境構築・スキーマ検証・PyInstaller単一EXEビルドタスク
│   ├── launch.json                   # デバッグ実行設定
│   └── settings.json                 # Python / Copilot 設定
├── src/
│   ├── server.py                     # FastMCP サーバー本体（M365互換フラットスキーマ・Streamable HTTP :8765）
│   ├── tray_launcher.py              # 非エンジニア向けオンデマンドGUIランチャー（終了ボタン・保存先を開くボタン付き）
│   ├── ps_com/
│   │   ├── controller.py             # win32com + CoInitialize スレッドセーフ制御クラス
│   │   └── jsx_templates.py          # 単一EXE埋め込み用 ExtendScript (レイヤー構造JSON解析・トリミング書き出し)
│   └── gateway/
│       └── router_gateway.py         # 【50名運用向け】M365単一URLから各社員PC(:8765)へ振り分けるリバースプロキシ雛形
├── m365_agent/
│   ├── declarativeAgent.json         # M365 Copilot 宣言型エージェント定義テンプレート
│   └── ai-plugin.json                # RemoteMCPServer プラグインマニフェスト
├── scripts/
│   ├── build_exe.ps1                 # PyInstaller でコンソールなしの単一EXE (ps-mcp-agent.exe) を生成するスクリプト
│   └── Start_Photoshop_MCP.bat       # ユーザー配布用オンデマンド起動バッチ
└── tests/
    └── test_schema_m365.py           # M365 Copilot が拒否する anyOf / $ref が混入していないか検査する自動テスト
```

---

## クイックスタート（VS Code + GitHub Copilot での開発手順）

1. **VS Code でこのフォルダを開く**
2. **タスクから仮想環境を作成 (`Ctrl+Shift+P` -> `Tasks: Run Task`)**
   - `1. 環境構築 (uv / venv & pip install)` を実行します。
3. **M365 スキーマ互換テストの実行**
   - `3. M365スキーマ互換性テスト (pytest)` を実行し、全ツールのスキーマがフラットであることを確認します。
4. **VS Code (GitHub Copilot Agent Mode) でローカル動作テスト**
   - `.vscode/mcp.json` が自動認識されるため、Copilot Chat (Agent Mode) から「今Photoshopで開いているPSDのレイヤー構造を解析して」と指示してCOM動作を確認できます。
5. **単一EXEのビルド**
   - `4. 単一EXEビルド (PyInstaller)` を実行すると、`dist/ps-mcp-agent.exe` が生成されます。
