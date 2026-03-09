# Implementation Plan: Extract `shinko` command and Refactor Architecture

## 1. 概要とゴール (Summary & Goal)
- **Must**: LLM インサイト機能を `kuroko` から独立した `shinko` コマンドに分離する。
- **Must**: 共通の定数・設定ロジックを `kuroko_core` パッケージに抽出する。
- **Must**: `kanpe` から `shinko` を CLI 経由で呼び出すようにし、コード上の直接的な依存を排除する。
- **Want**: `shinko` の出力を JSON で受け取り、`kanpe` UI でパースして表示する。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- **`kuroko_core/` (新規)**: `config.py`, `constants.py` を作成し、共通の設定・定数ロジックを移動。
- **`shinko/` (新規)**: `cli.py`, `llm.py` を作成し、LLM インサイト生成機能を実装。
- **`kuroko/` (修正)**: `shinko` サブコマンドを削除し、`kuroko_core` を参照するように修正。
- **`kanpe/` (修正)**: `LLMClient` への依存を削除。`/suggest` エンドポイントで `shinko` コマンドを実行するように変更。
- **`pyproject.toml` (修正)**: `kuroko_core` パッケージの追加と `shinko` エントリポイントの登録。

### ⛔ Non-Goals (やらないこと/スコープ外)
- **新機能の追加**: LLM プロンプトの改善や新しいインサイト機能の追加は行わない。
- **UI の大幅な変更**: `kanpe` のデザイン変更などは行わない。
- **外部依存の追加**: 既存のライブラリ（`click`, `pydantic`, `yaml` 等）の範囲内で実装する。

## 3. 実装ステップ (Implementation Steps)

1. [ ] **Step 1: `kuroko_core` パッケージの作成と移行**
   - `kuroko_core/` ディレクトリと `__init__.py` を作成。
   - `kuroko/config.py` と `kuroko/constants.py` を `kuroko_core/` へ移動。
   - `kuroko/` および `kanpe/` 内のインポート文を `kuroko_core` を参照するように一括置換。
   - *Validation*: `kuroko --help`, `kanpe --help` が正常に動作すること。

2. [ ] **Step 2: `shinko` パッケージの作成と機能移譲**
   - `shinko/` ディレクトリと `__init__.py` を作成。
   - `kuroko/llm.py` を `shinko/llm.py` に移動し、`kuroko_core` を参照するように修正。
   - `shinko/cli.py` を新規作成し、`kuroko/cli.py` の `shinko` サブコマンドの内容を移植（独立した `main` コマンドとして定義）。
   - `pyproject.toml` に `shinko = "shinko.cli:main"` を追加。
   - *Validation*: `pip install -e .` 後、`shinko --help` が動作すること。

3. [ ] **Step 3: `kuroko` からの LLM 依存排除**
   - `kuroko/cli.py` から `shinko` サブコマンド定義を削除。
   - 不要になった `kuroko/llm.py` を削除。
   - *Validation*: `kuroko` コマンドに `shinko` サブコマンドが表示されないこと。

4. [ ] **Step 4: `kanpe` の修正（疎結合化）**
   - `kanpe/cli.py` から `LLMClient` のインポートと直接使用を削除。
   - `/suggest` ハンドラ内で `subprocess.run(["shinko", "--input-file", report_path, "--json-output"], ...)` を実行し、結果の JSON をパースしてレスポンスを生成するように変更。
   - *Validation*: `kanpe` 画面から「次の一手を提案」をクリックし、従来通り提案が表示されること。

## 4. 検証プラン (Verification Plan)
- **単体テスト**: `tests/` 内の既存テストがすべて通ること。
- **結合テスト**:
  1. `kuroko report` でレポートを作成。
  2. `shinko --input-file report.md` でインサイトが表示されることを確認。
  3. `kanpe` を起動し、ブラウザ上で提案機能が動作することを確認。

## 5. ガードレール (Guardrails for Coding Agent)
- 各コマンド (`kuroko`, `shinko`, `kanpe`) は、お互いの内部コードをインポートしてはならない。
- 共有すべきは `kuroko_core` のみとする。
- 設定ファイル `kuroko.config.yaml` の読み込みロジックは `kuroko_core` に集約し、各コマンドで一貫した設定を利用できるようにする。
