# Implementation Plan: 注目プロジェクトの記録とLLMインサイトへの活用 (秘書コンテキスト機能)

## 1. 概要とゴール (Summary & Goal)
- **Must**: kanpe の提案（/suggest）実行時に、対象プロジェクトやモード、タイムスタンプ、リポジトリ情報を履歴として記録する。
- **Must**: 履歴の保存先を `~/.config/kuroko/history.jsonl` とし、設定ファイル（kuroko.config.yaml）で変更可能にする。
- **Must**: shinko 実行時に直近の履歴から作業傾向を要約し、LLMへのプロンプトに「秘書からのコンテキスト」として注入する。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- **`kuroko_core/config.py`**:
    - `KurokoConfig` に `history_path` フィールドを追加（デフォルト: `~/.config/kuroko/history.jsonl`）。
- **`kuroko_core/history.py` (新規)**:
    - `HistoryLogger`: イベント（timestamp, repo_root, project, mode）を JSONL 形式で追記保存する。
    - `HistorySummarizer`: 履歴ファイルを読み込み、直近 N 件の統計（プロジェクト頻度、モード傾向）をプロンプト用テキストに変換する。
- **`kanpe/cli.py`**:
    - `/suggest` エンドポイント成功時に `HistoryLogger` を呼び出して記録する。
- **`shinko/cli.py`**:
    - インサイト生成前に `HistorySummarizer` を実行し、LLMのプロンプトにコンテキストを挿入する。
- **テストの追加**:
    - 履歴の記録、読み込み、要約ロジックの単体テストを追加。

### ⛔ Non-Goals (やらないこと/スコープ外)
- **履歴の可視化 (UI)**: 今回はプロンプト注入のみとし、Web UI上でのグラフ表示などは行わない。
- **高度な解析**: 単純な頻度統計に留め、複雑な機械学習等による解析は行わない。
- **履歴の削除/編集機能**: 今回は追記のみとする。

## 3. 実装ステップ (Implementation Steps)
1.  [ ] **Step 1: `kuroko_core` の基盤整備**
    - *Action*: `config.py` 修正。`history.py` 新規作成。
    - *Validation*: `tests/test_history.py` を作成し、正しいパスへの保存と要約生成を確認。
2.  [ ] **Step 2: `kanpe` での記録実装**
    - *Action*: `/suggest` ハンドラ内に `HistoryLogger.log_event()` を組み込む。
    - *Validation*: 実際に提案を実行し、履歴ファイルが正しく生成されるか確認。
3.  [ ] **Step 3: `shinko` でのコンテキスト注入**
    - *Action*: プロンプト生成前に履歴を読み込み、`system` プロンプトの冒頭に「ユーザーの最近の傾向」として挿入。
    - *Validation*: LLMへのリクエスト内容（サーバーログ等）に履歴情報が含まれていることを確認。

## 4. 検証プラン (Verification Plan)
- `uv run pytest` が全て通ること。
- 手動確認:
    1. `kanpe` で「🚀 通常」ボタンを押す（複数回）。
    2. `history.jsonl` に正しく行が追加されているか確認。
    3. `shinko` を実行し、提案内容に「最近の傾向を踏まえた」アドバイスが含まれるか（またはプロンプトに含まれているか）を確認。

## 5. ガードレール (Guardrails for Coding Agent)
- 既存のテストを壊さないこと。
- パス解決（`~` や相対パス）は `os.path.expanduser` や `Path.resolve()` を適切に使用すること。
- JSONLの読み書き時は、ファイルが存在しない場合や空の場合を適切にハンドリングすること。
