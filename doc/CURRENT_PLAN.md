# Implementation Plan: kuroko report command

## 1. 概要とゴール (Summary & Goal)
収集したチェックポイントから、人間が読みやすい Markdown 形式のレポートを生成する `report` コマンドを追加します。

- **Must**: 
    - 指定されたパスへの Markdown ファイル出力。
    - ステータス、ブロッカー、最近の活動の3セクションを含むレポート構成。
    - フィルタリング（日付、プロジェクト、Issue）機能の実装。
    - 折りたたみセクション（`<details>`）やテーブルを用いた整形。
- **Want**:
    - 出力ファイルが既に存在する場合の `--overwrite` / `--no-overwrite` 制御（今回はデフォルト上書きとする）。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- **`kuroko/collector.py` の拡張**: フィルタリングロジックの追加（since, until, project, issue）。
- **`kuroko/reporter.py` の新規作成**: Markdown レポートの生成ロジック。
- **`kuroko/cli.py` への `report` コマンド追加**: 各種オプション（--since, --include-path等）の実装。
- **検証用テスト**: フィルタリングとレポート生成の単体テスト。

### ⛔ Non-Goals (やらないこと/スコープ外)
- **リファクタリング**: 既存の `recent`, `status` コマンドの出力形式の変更。
- **外部連携**: Slack や GitHub への自動投稿。
- **LLM 要約**: レポート内での LLM による自動要約（将来の拡張とする）。

## 3. 実装ステップ (Implementation Steps)

1. [ ] **Step 1: collector の機能強化**
    - *Action*: `kuroko/collector.py` の `collect_checkpoints` を拡張し、引数で `since`, `until`, `projects` (list), `issue`, `per_project_files` を受け取り、フィルタリングするように修正。
    - *Validation*: `tests/test_collector.py` を作成し、日付やプロジェクトによるフィルタが正しく機能することを確認。

2. [ ] **Step 2: reporter モジュールの作成**
    - *Action*: `kuroko/reporter.py` を作成。`doc/second_idea.md` の仕様（Header, Status Table, Blockers List, Recent Section）に沿った Markdown 文字列を生成する関数を実装。
    - *Validation*: `tests/test_reporter.py` を作成し、サンプルエントリから期待通りの Markdown が生成されるか確認。

3. [ ] **Step 3: CLI コマンドの実装**
    - *Action*: `kuroko/cli.py` に `@main.command() def report` を追加。ファイル出力処理と `reporter.py` の呼び出しを実装。
    - *Validation*: `kuroko report output.md` を実行し、ファイルが生成されることを確認。

4. [ ] **Step 4: ドキュメント更新**
    - *Action*: `README.md` に `report` コマンドの使い方を追記。

## 4. 検証プラン (Verification Plan)
- **単体テスト**: `pytest tests/test_collector.py tests/test_reporter.py` を実行。
- **実機確認**: 
    1. 既存の `checkpoint/` ディレクトリがある状態で `kuroko report test_report.md` を実行。
    2. 生成された `test_report.md` を VSCode 等で開き、テーブルやリストが正しく表示されるか確認。
    3. `--since` や `--issue` などのフィルタを適用して、内容が絞り込まれるか確認。

## 5. ガードレール (Guardrails for Coding Agent)
- 既存の `recent`, `status`, `blockers` コマンドが壊れないようにすること（`collector.py` の変更時はデフォルト引数に注意）。
- `PyYAML` や `click` 以外の新しいライブラリは導入しない。
