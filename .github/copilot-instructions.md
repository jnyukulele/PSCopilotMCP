# GitHub Copilot 開発指示書 (Photoshop MCP Server for M365 Copilot - 50 Users On-Demand Edition)

## プロジェクト概要
部署内の約50名の非エンジニア（デザイナー・企画職等）が、**Microsoft 365 Copilot App** から自身のローカルPC上の **Adobe Photoshop** を操作し、「PSD内部のレイヤー構造解析・画像アセット書き出し」を行うための **Windows COM (`win32com`) ベース単一EXE化 MCPサーバー** および **50名マルチユーザールーティング基盤** の開発ハーネスです。

## アーキテクチャおよび厳守すべき設計原則

1. **責務の分離 (Separation of Concerns)**
   - **MCP Tool Router Layer (`src/server.py`)**: FastMCPによるツール定義と入出力のフラット化。ロジックを持たず、`PsController` を呼び出すだけにする。
   - **Photoshop COM / ActionManager Layer (`src/ps_com/controller.py`)**: `win32com.client` と `pythoncom.CoInitialize()` によるスレッドセーフなCOM通信。レイヤー走査や書き出しはCOMオーバーヘッドを避けるため、`app.DoJavaScript()` 経由で ExtendScript (`ActionManager` / JSON) を一括実行して決定論的に処理する。
   - **On-Demand Tray Launcher (`src/tray_launcher.py`)**: Windowsスタートアップには登録せず、ユーザーが利用時のみダブルクリックで起動するタスクトレイ常駐ラッパー（またはコンソールレス起動）。終了時はワンクリックでポートとトンネルを閉じる。

2. **M365 Copilot プラグイン（Declarative Agent）のスキーマ制約【最重要】**
   - M365 Copilot のオーケストレーターおよび Microsoft 365 Agents Toolkit は、**ネストされた複雑なJSONスキーマ（`anyOf`, `oneOf`, `allOf`, `$ref`, 辞書型の不定キー、Union型）をサポートしません**。
   - Pythonの `Optional[str] = None` は Pydantic / FastMCP で `anyOf: [{type: string}, {type: null}]` を生成し、M365 Copilot取り込み時にスキーマ検証エラーを起こす原因になります。
   - **対策**: すべてのMCPツール引数は **`str`, `int`, `bool` のプリミティブ型のみ** とし、省略可能パラメータには `str = ""` や `int = 0` のような空文字・ゼロのデフォルト値を与えて `Optional` (`Union[..., None]`) を一切排除してください。
   - ツール総数はM365 Copilotの推論精度維持のため **最大10個以内** に厳選してください。

3. **COM スレッドセーフティ（Streamable HTTP 対応）**
   - `FastMCP` を `streamable-http` で動かすと、リクエストは非同期ワーカースレッドで処理されます。
   - COMオブジェクト (`Photoshop.Application`) を触る関数・コンテキストでは、必ず `pythoncom.CoInitialize()` と `pythoncom.CoUninitialize()` をペアで実行するコンテキストマネージャ (`com_context()`) を経由させてください。

4. **50名規模でのM365 Copilot接続アーキテクチャ**
   - M365 Copilot の Declarative Agent はマニフェストに単一のHTTPS URLを持ちます。
   - **方式A（推奨：社内ゲートウェイ集約型）**: M365 Copilot は社内リバースプロキシ (`src/gateway/router_gateway.py`) の単一HTTPSエンドポイントを呼び出し、ヘッダーまたはユーザーのマシン識別子（またはDevTunnel/Tailscale/社内DNS名）に応じて各ユーザーのPC (`port 8765`) へルーティングする。
   - **方式B（個別DevTunnel型）**: オンデマンド起動バッチ (`scripts/Start_Photoshop_MCP.bat`) が `ps-mcp-agent.exe` と `devtunnel` を同時起動し、ユーザー固有のトンネルタグで待ち受ける。

5. **PyInstaller 単一EXE化への配慮**
   - 外部 `.jsx` ファイルや設定を同梱する場合は `sys._MEIPASS` に対応したパス解決ヘルパーを使用するか、ExtendScript文字列をPythonモジュール (`src/ps_com/jsx_templates.py`) に定数として埋め込み、ファイルI/O依存をなくしてください。
