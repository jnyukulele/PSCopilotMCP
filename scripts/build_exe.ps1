# PyInstaller を用いて配布用の単一EXE (ps-mcp-agent.exe) をビルドするスクリプト
$ErrorActionPreference = "Stop"

Write-Host "=== Building Single EXE for Non-Technical Users (ps-mcp-agent.exe) ===" -ForegroundColor Cyan

if (-Not (Test-Path ".venv\Scripts\pyinstaller.exe")) {
    Write-Host "Installing dependencies into .venv..."
    python -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
}

# GUIステータスウィンドウ付き（黒いコンソール画面を非表示にした --noconsole モード）でEXE化
Remove-Item "ps-mcp-agent.spec" -Force -ErrorAction SilentlyContinue
Remove-Item "dist\ps-mcp-agent.exe" -Force -ErrorAction Stop
& ".\.venv\Scripts\python.exe" -m PyInstaller "--clean" "--noconfirm" "--onefile" "--noconsole" "--name" "ps-mcp-agent" "--hidden-import" "win32com" "--hidden-import" "win32com.client" "--hidden-import" "pythoncom" "--hidden-import" "uvicorn.logging" "--hidden-import" "uvicorn.loops.auto" "--hidden-import" "uvicorn.protocols.http.auto" "src\tray_launcher.py"
if (-Not (Test-Path "dist\ps-mcp-agent.exe")) {
    throw "PyInstaller did not produce dist\ps-mcp-agent.exe."
}

# コンソール版（CLI / トンネル併用デバッグ用）も同時にビルドしたい場合は以下を有効化
# .\.venv\Scripts\pyinstaller.exe --noconfirm --onefile --name "ps-mcp-cli" src\server.py

Copy-Item "scripts\Start_Photoshop_MCP.bat" "dist\Start_Photoshop_MCP.bat" -Force
Write-Host "=== Build Complete! 配布用ファイルは dist\ フォルダに出力されました ===" -ForegroundColor Green
