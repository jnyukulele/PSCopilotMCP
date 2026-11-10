"""
M365 Copilot Declarative Agent 互換スキーマ検証テスト。
- 登録されているツール数が上限（10個以下）に収まっているか
- M365 Copilot が拒否する `anyOf`, `oneOf`, `allOf`, `$ref` が JSON Schema に含まれていないか
を自動テストします。
"""
import asyncio
from src.server import mcp


def test_m365_copilot_schema_compatibility():
    tools = asyncio.run(mcp.list_tools())
    assert 1 <= len(tools) <= 10, f"ツール数は1〜10個に絞る必要があります（現在: {len(tools)}個）"

    forbidden_keys = {"anyOf", "oneOf", "allOf", "$ref"}

    def find_forbidden_keys(obj, path=""):
        found = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                current_path = f"{path}.{k}" if path else k
                if k in forbidden_keys:
                    found.append(current_path)
                found.extend(find_forbidden_keys(v, current_path))
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                found.extend(find_forbidden_keys(item, f"{path}[{idx}]"))
        return found

    for tool in tools:
        schema = tool.inputSchema
        violations = find_forbidden_keys(schema)
        assert not violations, (
            f"ツール '{tool.name}' のスキーマに M365 Copilot 非互換キー {violations} が含まれています。"
            "引数から Optional[T] / Union を排除し、プリミティブ型のデフォルト値（str = '' 等）に変更してください。"
        )
