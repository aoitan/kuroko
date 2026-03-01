# Implementation Plan: `kuroko worklist` Subcommand

## 1. 概要とゴール (Summary & Goal)
GitHub リポジトリから Open な PR と Issue を取得し、プロジェクトごとに一覧表示するサブコマンド `kuroko worklist` を追加する。

- **Must**:
  - `kuroko.config.yaml` への `repo` フィールド（owner/repo 形式）の追加。
  - `gh` コマンドを使用した PR/Issue データの取得。
  - Markdown テーブル形式での標準出力。
  - `--json-output` オプションによる JSON 形式での出力。
- **Want**:
  - `gh` コマンドがインストールされていない場合の適切なエラーメッセージ。
  - Stale アイテム（最終更新から 7 日以上経過）のハイライトまたは統計。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- `kuroko/config.py`: `ProjectConfig` クラスへの `repo: Optional[str] = None` フィールドの追加。
- `kuroko/worklist.py` (新規): `gh` コマンド呼び出しとデータ構造化ロジックの追加。
- `kuroko/cli.py`: `worklist` サブコマンドの実装と `main` への登録。
- 出力フォーマットの実装（Markdown / JSON）。

### ⛔ Non-Goals (やらないこと/スコープ外)
- GitHub 以外のプラットフォーム（GitLab, Bitbucket 等）への対応。
- `gh` コマンド以外の方法（直接 API を叩く等）によるデータ取得。
- PR/Issue の詳細なフィルタリング機能（サブコマンドのオプションとして複雑なクエリを渡すなど）。

## 3. 実装ステップ (Implementation Steps)
1. [ ] **Step 1: 設定ファイルの拡張**
   - *Action*: `kuroko/config.py` の `ProjectConfig` に `repo` フィールドを追加。
2. [ ] **Step 2: データ取得ロジックの実装**
   - *Action*: `kuroko/worklist.py` を新規作成。`subprocess` を介して `gh pr list` および `gh issue list` を実行し、指定された項目（ID, タイトル, 更新日時等）をパースする関数を作成。
   - *Validation*: ダミーのリポジトリ設定を用いて、正しくリストが取得・パースされるかテスト。
3. [ ] **Step 3: CLI サブコマンドの追加**
   - *Action*: `kuroko/cli.py` に `@main.command()` として `worklist` を追加。取得したデータをプロジェクトごとにループして Markdown テーブルで出力する。
   - *Validation*: `kuroko worklist` 実行時に Markdown が出力されることを確認。
4. [ ] **Step 4: JSON 出力対応**
   - *Action*: `--json-output` フラグがある場合に、パース済みのオブジェクトを JSON 形式で print する。

## 4. 検証プラン (Verification Plan)
- `kuroko worklist` を実行し、Markdown 形式でプロジェクト名、統計、PR/Issue リストが表示されること。
- `kuroko worklist --json-output` を実行し、有効な JSON が出力されること。
- リポジトリが設定されていないプロジェクトがある場合、スキップされるか適切な警告が出ること。

## 5. ガードレール (Guardrails for Coding Agent)
- `gh` コマンドへの依存を最小限にし、コマンドの実行失敗時（未ログイン等）にクラッシュしないようエラーハンドリングを徹底すること。
- 既存の `kuroko status` や `recent` のコードスタイルに合わせること。
