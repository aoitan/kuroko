# kuroko

各リポジトリに散らばる「証跡（checkpoint）」を収集・可視化するためのCLIツール。
複数のプロジェクトの進捗や、現在発生しているブロック（詰まり）を一目で把握することを目的とする。

## テックスタック
- Python (>=3.9)
- Click (CLI)
- Pydantic (Data validation)
- PyYAML (Config)
- Markdown (Report)
- pytest (Testing)
- SQLite (DB)
- uv (Package management)

## プロジェクト構造
- `kuroko/`: コアロジックとCLI。
- `kuroko_core/`: 共通のDB、設定、定数、履歴管理。
- `shinko/`: 分析・推論。
- `kanpe/`: UI・レポート生成。
- `tests/`: テスト。
- `doc/`: ドキュメント。
