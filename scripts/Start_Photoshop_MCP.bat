@echo off
chcp 65001 > nul
title Photoshop × M365 Copilot オンデマンド起動ランチャー

echo ========================================================
echo  Photoshop × M365 Copilot 連携を起動しています...
echo  ※Windows起動時には常駐せず、このバッチを開いた時だけ稼働します。
echo ========================================================

REM 1. 単一EXE化されたMCPエージェントを起動（ポート8765）
REM 開発用 scripts フォルダから起動した場合も、最新の dist 版を優先します。
if exist "%~dp0..\dist\ps-mcp-agent.exe" (
    start "" "%~dp0..\dist\ps-mcp-agent.exe"
) else if exist "%~dp0ps-mcp-agent.exe" (
    start "" "%~dp0ps-mcp-agent.exe"
) else (
    echo [開発モード] Pythonスクリプトから直接起動します...
    start "" "%~dp0..\.venv\Scripts\pythonw.exe" "%~dp0..\src\tray_launcher.py"
)

REM 2. 個人別DevTunnelやCloudflare Tunnelをオンデマンドで同時起動する場合は以下のコメントを解除
REM devtunnel host -p 8765 --allow-anonymous

exit
