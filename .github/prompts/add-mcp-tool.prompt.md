---
mode: 'agent'
description: 'M365 Copilotのスキーマ制約（フラット型・Optional禁止）に準拠した新しいPhotoshop COMツールを追加する'
---
新しいPhotoshop操作用MCPツールを追加してください。以下のルールを厳守すること：

1. `src/ps_com/jsx_templates.py` に、Photoshop内で高速に動作する ExtendScript (ActionManager または DOM) のテンプレート文字列を追加する。返り値は `JSON.stringify()` でシリアライズした文字列とすること。
2. `src/ps_com/controller.py` の `PhotoshopController` クラスに、`with self._com_session() as app:` を使って `app.DoJavaScript()` を呼び出すメソッドを追加する。
3. `src/server.py` に `@mcp.tool()` デコレータでツールを公開する。
   - **重要**: M365 Copilot互換のため、引数に `Optional` や `None` デフォルト値を絶対に使わないこと（例: `layer_filter: str = ""` のようにプリミティブ型のデフォルト値を使う）。
   - Docstringには、PCに詳しくないユーザーがM365 Copilot上で自然言語で指示した際にマッチしやすい日本語の説明を記述すること。
4. `tests/test_schema_m365.py` を実行し、生成されるJSONスキーマに `anyOf` や `$ref` が含まれないことを検証すること。
