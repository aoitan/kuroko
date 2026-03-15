# Implementation Plan: Phase 1: 最小収集基盤 (`memo.md` 巡回と原文DB保存) (#17)

## 1. 概要とゴール (Summary & Goal)
- **Must**: 
  - `kuroko collect memo` サブコマンドを追加する。
  - `KurokoConfig` の `projects[].root` 配下にある `memo.md` ファイルを再帰的に走査し、SQLite DB に保存する。
  - 同一ファイル（ハッシュ値が同じ場合）の重複インポートを防ぐ。
- **Want**: 
  - メモ内容のパースや要約などの高度な処理（今回は対象外）。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- SQLite DB (`~/.config/kuroko/kuroko.db` 等) の初期化処理の実装。
- `source_texts` テーブルのスキーマ定義とCRUD処理。
- `kuroko/cli.py` に `collect` グループおよび `memo` コマンドを追加。
- `memo.md` を走査して、ハッシュ値ベースで重複チェックを行い、新規/更新分をDBへ保存するコレクターロジック (`kuroko/memo_collector.py` などを新設)。
- SQLite操作モジュール (`kuroko_core/db.py` などを新設)。
- 単体テストの追加。
- `KurokoConfig` へ `db_path` の定義追加。

### ⛔ Non-Goals (やらないこと/スコープ外)
- **リファクタリング**: 今回の変更に関係のない箇所のコード整理は行わない。
- **追加機能**: `memo.md` 以外のファイル（例: `README.md`）の収集。収集したメモの要約やAI解析機能。
- **依存関係**: Python標準の `sqlite3`, `hashlib`, `glob`, `pathlib` などを利用し、SQLAlchemy などの巨大な外部ORMは導入しない。

## 3. 実装ステップ (Implementation Steps)
1.  [ ] **Step 1**: 設定とデータベース基盤の作成
    - *Action*: `kuroko_core/config.py` の `KurokoConfig` に `db_path: str = "~/.config/kuroko/kuroko.db"` を追加。
    - *Action*: `kuroko_core/db.py` を新規作成し、DB初期化 (`init_db`) と `source_texts` テーブルを作成するDDLを実装。
      - `id`, `source_type`, `path`, `directory_context`, `raw_text`, `file_hash`, `updated_at`, `imported_at`
    - *Validation*: `tests/test_db.py` を作成し、メモリDB (`:memory:`) または一時ファイルを用いた初期化テストを実装。
2.  [ ] **Step 2**: コレクターロジックの実装
    - *Action*: `kuroko/memo_collector.py` を新規作成し、指定プロジェクト配下の `memo.md` を検索する処理を実装。
    - *Action*: ファイルのハッシュ (SHA-256など) を計算し、DBの `file_hash` と比較して未インポートまたは更新されたファイルのみを `source_texts` に INSERT/UPDATE する処理を実装。
    - *Validation*: `tests/test_memo_collector.py` を作成。一時ディレクトリにダミーの `memo.md` を配置し、収集と重複防止の挙動をテスト。
3.  [ ] **Step 3**: CLIコマンドの追加
    - *Action*: `kuroko/cli.py` に `@click.group() def collect()` を追加し、メインに登録。その下に `@collect.command() def memo()` を定義。
    - *Action*: `KurokoConfig` を受け取り、DB初期化後に各プロジェクトに対して `memo_collector` を実行するよう連携。
    - *Validation*: `tests/test_cli_collect.py` を作成し、`CliRunner` を用いてコマンドの呼び出しと出力内容をテスト。

## 4. 検証プラン (Verification Plan)
- `pytest` ですべてのテスト（既存テストおよび新規追加した `test_db.py`, `test_memo_collector.py`, `test_cli_collect.py`）がパスすること。
- 手動確認:
  1. `kuroko.config.yaml` が設定された状態で、プロジェクト配下にテスト用の `memo.md` を作成する。
  2. `kuroko collect memo` を実行し、SQLite DB にレコードが保存されることを確認する。
  3. 再度 `kuroko collect memo` を実行し、新規インポート件数が0件（スキップ）となることを確認する。
  4. `memo.md` の内容を変更後、`kuroko collect memo` を実行し、DBが更新されることを確認する。

## 5. ガードレール (Guardrails for Coding Agent)
- 既存のロジックを変更する場合は、必ずコメントで理由を残すこと。
- この計画に含まれないファイルの変更は禁止する。
- 外部のデータベースライブラリやORMを追加しないこと。標準の `sqlite3` モジュールを利用すること。
- TDDワークフロー (`doc/development_workflow.md`) に従い、先に失敗するテストを書いてから実装を進めること。
