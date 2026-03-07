# Implementation Plan: Worklist 統計情報を Open 全件数にする

## 1. 概要とゴール (Summary & Goal)
`kuroko worklist` および `kanpe` の表示において、Open な PR/Issue の**実際の総数**を表示する。

- **Must**:
  - `fetch_worklist` が、最新のリスト（5件など）に加えて、Open な全件数（総数）を返すようにする。
  - レポートの Summary 表示を `Summary: 12 Open PRs (showing latest 5)` のような形式に更新。
  - `kuroko worklist` の標準出力および `--json-output` に総数を含める。
- **Want**:
  - `gh search` または `gh api` を使用した効率的なカウント取得。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- `kuroko/worklist.py`: 
  - 総数を取得するための関数 `_run_gh_total_count` を追加。
  - `fetch_worklist` の戻り値に `total_pull_requests` と `total_issues` を追加。
- `kuroko/cli.py`: `worklist` サブコマンドの出力を、総数を含む形式に修正。
- `kuroko/reporter.py`: `generate_report` の Worklist セクションのレンダリングを、総数を含む形式に修正。

### ⛔ Non-Goals (やらないこと/スコープ外)
- Closed なアイテムのカウント取得。
- ラベルごとの詳細なカウント。

## 3. 実装ステップ (Implementation Steps)
1. [ ] **Step 1: 総数取得ロジックの実装**
   - *Action*: `kuroko/worklist.py` に `_run_gh_total_count` を実装。`gh search pr --repo {repo} --state open --limit 0` 等を使用。
   - *Validation*: テストで実際の（またはモックされた）総数が正しく取得できることを確認。
2. [ ] **Step 2: データの統合**
   - *Action*: `fetch_worklist` を更新。
   - *Validation*: `tests/test_worklist.py` を更新。
3. [ ] **Step 3: CLI 出力の更新**
   - *Action*: `kuroko/cli.py` の Markdown 出力を修正。
4. [ ] **Step 4: Reporter の更新**
   - *Action*: `kuroko/reporter.py` を修正し、`Summary: {total} Open PRs (showing latest {count})` 形式に変更。

## 4. 検証プラン (Verification Plan)
- `kuroko worklist` を実行し、文言とともに全件数が表示されること。
- `kuroko worklist --json-output` で JSON 構造を確認。

## 5. ガードレール (Guardrails for Coding Agent)
- `gh search` がエラーになった場合は、単にリストの件数を総数として扱うなどのエラー耐性を持たせること。
