# Implementation Plan: Issue #21 Embedding DB

## 1. 概要とゴール (Summary & Goal)
- **Must**: chunk 単位の埋め込み派生データを SQLite 内に保持できるようにし、`kuroko collect memo` 実行後に新規または更新 chunk のみ埋め込み更新できる基盤を入れる。
- **Must**: 原文 DB (`source_texts` / `chunks`) と埋め込みデータを `chunk_id` で関連付け、モデル差し替えや再生成を前提にしたスキーマと更新条件を定義する。
- **Must**: 任意の chunk を対象に類似 chunk 検索できる最小 API を用意し、後続の `shinko` / `kanpe` から再利用できる基盤にする。
- **Want**: 実運用の外部 embedding API 連携、複数ベクトル DB 対応、検索結果を使った UI/LLM 体験の改善。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- SQLite スキーマに埋め込み保存用テーブルを追加する。
  - 想定変更: `kuroko_core/db.py`, `tests/test_db.py`
- 埋め込みを「chunk から再生成可能な派生データ」として扱う更新ロジックを追加する。
  - 想定変更: `kuroko/memo_collector.py`, `kuroko/cli.py`, `tests/test_memo_collector.py`, `tests/test_cli_collect.py`
- 埋め込み生成のための最小インターフェース層を追加する。
  - 想定変更: `kuroko_core/config.py`, `kuroko_core/embeddings.py` または同等の新規モジュール, 対応テスト
- 新規/更新 chunk のみ更新する差分判定を導入する。
  - `chunk_hash` と `embedding_model` と `chunking_version` の組み合わせで再生成要否を判断する。
- 類似 chunk 検索の最小 API を追加する。
  - 想定変更: `kuroko_core/db.py` または専用モジュール, 対応テスト
- 設計と利用前提をドキュメント化する。
  - 想定変更: `doc/arch/memo_collection_db.md`, `README.md`

### ⛔ Non-Goals (やらないこと/スコープ外)
- **外部 Vector DB 導入**: Chroma / Qdrant / pgvector 等への移行は行わない。まずは既存 SQLite 内で成立させる。
- **本格的な検索 UI 統合**: `kanpe` 画面や `shinko` プロンプトの大幅改修は行わない。
- **広い責務分離**: Phase 4 相当の CLI 再設計やサブコマンド再編は行わない。
- **高度な埋め込み運用**: バッチ再生成 CLI、バックグラウンドジョブ、複数モデルの同時保持ポリシー最適化までは扱わない。
- **別件リファクタリング**: memo/chunk 既存処理の unrelated cleanup は行わない。

## 3. 設計方針 (Design Decisions)
- 埋め込みデータは `chunks` テーブルに直接混在させず、別テーブルで管理する。
  - 理由: 原文 DB と派生データの責務を分け、モデル差し替え時の再生成や削除を扱いやすくするため。
- ベクトル本体は SQLite に保存できる単純な形式で持つ。
  - 第一候補: JSON 文字列。
  - 理由: 追加依存なしで実装でき、テストでも扱いやすい。
- 類似検索は最初はアプリケーション層で計算する。
  - 理由: SQLite 単体ではベクトル類似検索の専用機能がないため。まずは少量データで成立する基盤を優先する。
- 埋め込み生成器は差し替え可能なインターフェースに切る。
  - 理由: 現時点で embedding 用ライブラリ依存がなく、後から実 API に接続できるようにするため。
- `chunking_version` は埋め込みレコードに持たせる。
  - 理由: chunk 分割ルール変更時に「同じ chunk_id でも再生成が必要」という判定を可能にするため。

## 4. 実装ステップ (Implementation Steps)
1. [ ] **Step 1**: 埋め込みテーブルのスキーマを定義する
   - *Action*: `kuroko_core/db.py` に `chunk_embeddings` テーブルを追加する。
   - *Action*: 必須カラムを `chunk_id`, `embedding`, `embedding_model`, `embedded_at`, `chunking_version` とし、`chunks(id)` への外部キーと必要インデックスを定義する。
   - *Validation*: `tests/test_db.py` でテーブル作成、カラム、インデックス、外部キー前提を検証する。

2. [ ] **Step 2**: 埋め込み設定と生成インターフェースを追加する
   - *Action*: `kuroko_core/config.py` に embedding 用設定モデルを追加する。
   - *Action*: `kuroko_core/embeddings.py` などに `embed_texts()` 相当の最小抽象化を追加する。
   - *Action*: テストでは deterministic なダミー embedder を使い、外部 API に依存しない。
   - *Validation*: 設定ロードと embedder 呼び出しの単体テストを追加する。

3. [ ] **Step 3**: memo collect 時の差分埋め込み更新を実装する
   - *Action*: `kuroko/memo_collector.py` で chunk 保存後に埋め込み更新処理を呼ぶ。
   - *Action*: 新規 chunk、`chunk_hash` 変更 chunk、`embedding_model` 変更 chunk、`chunking_version` 不一致 chunk のみ再生成する。
   - *Action*: source 更新時に削除された chunk に紐づく古い埋め込みが残らないことを保証する。
   - *Validation*: `tests/test_memo_collector.py` に新規作成時、再実行スキップ時、更新時、モデル変更時のテストを追加する。

4. [ ] **Step 4**: `kuroko collect memo` から埋め込み更新までを一貫実行にする
   - *Action*: `kuroko/cli.py` の `collect memo` 経由で embedding 更新まで完了するよう接続する。
   - *Action*: 将来の差し替えに備え、CLI 層は設定解決と orchestration のみを持つ。
   - *Validation*: `tests/test_cli_collect.py` に埋め込みレコード作成と再実行スキップの観点を追加する。

5. [ ] **Step 5**: 類似 chunk 検索の最小 API を追加する
   - *Action*: `chunk_id` またはクエリ文字列から埋め込み済み chunk を取得し、コサイン類似度などで近傍を返す API を追加する。
   - *Action*: 最初は内部利用向け関数として実装し、CLI や UI への露出は後続タスクに委ねる。
   - *Validation*: 類似度順に chunk が返ること、対象 chunk 自身の除外条件を制御できることをテストする。

6. [ ] **Step 6**: ドキュメントを更新する
   - *Action*: `doc/arch/memo_collection_db.md` に派生データテーブルと更新ルールを追記する。
   - *Action*: `README.md` に embedding 設定と collect 後の期待動作を簡潔に追記する。
   - *Validation*: ドキュメントが実装済みのコマンドとデータモデルに一致していることを確認する。

## 5. 検証プラン (Verification Plan)
- `docker compose run --rm dev uv run pytest tests/test_db.py tests/test_memo_collector.py tests/test_cli_collect.py`
- 必要なら類似検索 API の専用テストを追加し、対象テストのみ個別実行する。
- 手動確認:
  1. テスト用 `memo.md` を 1 件収集する。
  2. `chunks` と `chunk_embeddings` の件数が一致することを確認する。
  3. 同内容で再実行し、埋め込み件数と `embedded_at` が不要に増えないことを確認する。
  4. `memo.md` を更新して再実行し、変更 chunk のみ再生成されることを確認する。

## 6. リスクと確認ポイント (Risks / Open Questions)
- 埋め込みモデルの実体が未確定。
  - 当面は差し替え可能な抽象化とダミー実装で進め、実 API 接続は別タスクで扱う前提が妥当。
- `chunk_id` の安定性は現在「行更新時に再採番されうる」。
  - 永続 ID の厳密運用が必要なら将来 `chunk_hash` ベースの再関連付け戦略を見直す余地がある。
- SQLite 内での類似検索は件数増加に弱い。
  - 今回は Phase 3 の基盤整備として許容し、検索性能要件が出た時点で別 Issue に切り出す。

## 7. ガードレール (Guardrails for Coding Agent)
- この計画に含まれない `kanpe` / `shinko` の大規模改修は行わない。
- 外部 API キー必須の実装にはしない。テストは完全にローカルで完結させる。
- 新しい依存ライブラリは、標準ライブラリと既存依存で不足する場合に限って追加可とする。その場合も理由を先に明示する。
- 既存の `source_texts` / `chunks` の意味論は維持し、原文を正本、埋め込みを派生データとして扱う。
- 実装開始時はこの計画書に書かれたファイル範囲を原則とし、追加変更が必要になったら先に計画を更新する。
