# Suggested Commands

## 開発用
- インストール: `uv tool install --editable .`
- テスト実行: `pytest`
- 全テスト実行: `pytest tests/`

## CLIコマンド
- 収集: `kuroko collect memo`
- 直近活動: `kuroko recent`
- ブロッカー: `kuroko blockers`
- ステータス: `kuroko status`
- レポート生成: `kuroko report report.md`
- Web UI表示: `kanpe --input-file report.md`
- LLMインサイト: `shinko --input-file report.md`
