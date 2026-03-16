# Implementation Plan: Phase 2: 原文の構造化とチャンク化 (#18)

## 1. 概要とゴール (Summary & Goal)
- **Must**: 
  - インポートされた `memo.md` などの原文テキストを、検索や解釈しやすい単位（チャンク）に分割する。
  - チャンク化の区切りは「空行」や「見出し」を基準とする。
  - チャンクデータごとにIDを付与し、元の原文と対応づけて `chunks` テーブルに保存する。
- **Want**: 
  - チャンク化の際に高度な意味解析を行うこと（今回は対象外とし、シンプルなルールベースとする）。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- `kuroko_core/db.py` への `chunks` テーブル追加（スキーマ定義）。
  - カラム: `id`, `source_id`, `chunk_index`, `chunk_text`, `heading`, `block_timestamp`, `chunk_hash`
- 新規モジュール `kuroko/chunker.py` の作成とチャンク化ロジックの実装。
  - 空行区切りおよび見出し（`#`）を考慮したテキストブロックの分割。
  - 分割されたチャンクごとに見出し（直前の見出し）やタイムスタンプ（抽出可能な場合）を保持するロジック。
- `kuroko/memo_collector.py` へのチャンク化処理の統合。
  - `collect` 実行時（`source_texts`への新規追加・更新時）に自動でチャンク化を行い、`chunks` テーブルへ保存（更新時は古いチャンクを削除後に再登録）。
- 関連する単体テストの追加・更新。

### ⛔ Non-Goals (やらないこと/スコープ外)
- **リファクタリング**: 今回の変更に関係のない箇所のコード整理は行わない。
- **追加機能**: LLMを用いた高度なチャンク化や、PDF等の他フォーマットのチャンク化対応。
- **依存関係**: 新しい外部ライブラリ（テキストパース用ライブラリ等）の追加は行わず、標準の文字列処理や正規表現を活用する。

## 3. 実装ステップ (Implementation Steps)
1.  [ ] **Step 1**: `chunks` テーブルの追加
    - *Action*: `kuroko_core/db.py` の `init_db` 内に、`chunks` テーブルを作成するDDLを追加。
    - *Action*: `source_texts` テーブルのIDを参照する `source_id` などを定義し、`chunk_hash` 等のインデックスを作成。
    - *Validation*: `tests/test_db.py` を修正・追加し、`chunks` テーブルが正しく作成されることを確認する。
2.  [ ] **Step 2**: チャンク化ロジックの実装
    - *Action*: `kuroko/chunker.py` を新規作成し、`chunk_text(text: str) -> List[Dict]` 関数を実装する。
    - *Action*: テキストを空行や見出しで分割し、辞書（`chunk_index`, `chunk_text`, `heading`, `block_timestamp`, `chunk_hash`）のリストを返すようにする。
    - *Validation*: `tests/test_chunker.py` を作成し、様々なパターンのマークダウンテキストが正しくチャンクに分割・メタデータ抽出されることをテストする。
3.  [ ] **Step 3**: チャンク化プロセスの統合
    - *Action*: `kuroko/memo_collector.py` にチャンク化処理を組み込む。
    - *Action*: 新規テキストの INSERT 時、および更新（UPDATE）時に、該当の `source_id` に紐づく古いチャンクを `DELETE` してから `chunk_text` で生成した新しいチャンクを `INSERT` する。
    - *Validation*: `tests/test_memo_collector.py` を更新し、1つの `memo.md` から複数チャンクが生成されDBに格納されること、原文との親子関係が保持されていることをテストする。

## 4. 検証プラン (Verification Plan)
- `pytest` ですべてのテスト（既存テストおよび新規追加した `test_chunker.py`, `test_db.py`, `test_memo_collector.py`）がパスすること。
- テスト内で「1つの `memo.md` から複数チャンクが生成されDBに格納されること」「原文との親子関係が正しく保持されていること」がアサーションされていること。

## 5. ガードレール (Guardrails for Coding Agent)
- 既存のロジックを変更する場合は、必ずコメントで理由を残すこと。
- TDDワークフロー (`doc/development_workflow.md`) に従い、先に失敗するテストを書いてから実装を進めること。
- チャンク化処理でエラーが発生した場合でも、collector 全体がクラッシュしないよう適切なエラーハンドリングを行うこと。