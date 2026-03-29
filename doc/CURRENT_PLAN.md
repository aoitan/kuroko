# Implementation Plan: 開発環境と実行環境のコンテナ化 (#29)

## 1. 概要とゴール (Summary & Goal)
- **Must**: `kuroko` / `kanpe` / `shinko` を、issue ごとの `git worktree` を `/workspace` に bind mount したコンテナで実行できるようにする。
- **Must**: 開発環境を壊しても、コンテナを破棄して再作成すればやり直せる構成にする。
- **Must**: 永続化すべき状態を worktree と `./.data` に分離し、コンテナ内部の壊れた状態を持ち越さないようにする。
- **Must**: 開発環境コンテナと実行環境コンテナを分け、`docker compose` で統一操作できるようにする。
- **Want**: Dev Container 対応、cron 実行の足場、キャッシュ最適化。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- `Dockerfile.dev` を追加し、開発用の Python/uv/pytest 実行環境を定義する。
- `Dockerfile` を追加し、`kuroko` / `kanpe` / `shinko` の実行向けランタイムを定義する。
- `compose.yaml` を追加し、dev/app/kanpe の実行モードを整理する。
- `.dockerignore` を追加し、不要ファイルを build context から除外する。
- worktree bind mount と `./.data` 永続化ディレクトリの運用を compose に反映する。
- `README.md` または `doc/` に、起動方法と「壊れたら捨ててやり直す」手順を追記する。

### ⛔ Non-Goals (やらないこと/スコープ外)
- **アプリ本体の機能追加**: `kuroko` / `kanpe` / `shinko` の機能拡張は行わない。
- **広いリファクタリング**: コンテナ化に直接必要ない CLI 再設計や DB スキーマ変更は行わない。
- **本番基盤**: Kubernetes、secrets 配布、監視、CI/CD 基盤の整備は行わない。
- **外部DB化**: SQLite 以外への移行は行わない。

## 3. 実装ステップ (Implementation Steps)
1. [ ] **Step 1**: 開発・実行コンテナの責務を固定する
   - *Action*: 既存の `README.md` と `pyproject.toml` を前提に、開発用と実行用に必要な依存・エントリポイント・作業ディレクトリを整理する。
   - *Validation*: どのコマンドを `Dockerfile.dev` と `Dockerfile` のどちらで受けるかが明確になること。

2. [ ] **Step 2**: 開発環境コンテナを設計・実装する
   - *Action*: `Dockerfile.dev` を追加し、`uv run pytest` と各 CLI の `uv run ...` が動く構成を作る。
   - *Action*: non-root 実行、`/workspace` 固定マウント、キャッシュ保存先を定義する。
   - *Validation*: `docker compose run --rm dev uv run pytest` が通ること。

3. [ ] **Step 3**: 実行環境コンテナを設計・実装する
   - *Action*: `Dockerfile` を追加し、最小ランタイムで `kuroko` / `kanpe` / `shinko` を個別 command として動かせるようにする。
   - *Action*: `kanpe` のポート公開前提を組み込む。
   - *Validation*: `docker compose run --rm app kuroko --help`、`docker compose run --rm app shinko --help`、`docker compose up kanpe` が成立すること。

4. [ ] **Step 4**: 永続化と再作成性を compose に落とす
   - *Action*: `compose.yaml` で worktree bind mount、`./.data` 永続化、必要な named volume を定義する。
   - *Action*: 設定、DB、レポート、checkpoint の mount ポリシーを明示する。
   - *Validation*: コンテナを削除して再作成しても `./.data` の内容が残り、再実行できること。

5. [ ] **Step 5**: build context と運用ドキュメントを整える
   - *Action*: `.dockerignore` を追加し、`.venv`、`__pycache__`、テスト生成物などを除外する。
   - *Action*: `README.md` または `doc/` に、基本操作、復旧手順、注意点を記載する。
   - *Validation*: 新規参加者が README だけで build、test、run、recreate の流れを追えること。

## 4. 検証プラン (Verification Plan)
- `docker compose build` が通ること。
- `docker compose run --rm dev uv run pytest` が通ること。
- `docker compose run --rm app kuroko --config /workspace/.data/config.yaml collect memo` が通ること。
- `docker compose run --rm app shinko --config /workspace/.data/config.yaml insight --input-file /workspace/.data/report.md` が通ること。
- `docker compose up kanpe` で `kanpe` UI を開けること。
- 開発コンテナ内の一時状態を壊した後でも、再作成で復旧できること。

## 5. ガードレール (Guardrails for Coding Agent)
- ホスト絶対パスを前提にした設定例を標準化しないこと。
- `projects[].root` はコンテナ内パスで扱う前提を崩さないこと。
- 生成物を worktree 直下へ散らばせず、`./.data` へ寄せること。
- Docker 実装のために既存 CLI の意味を変えないこと。
- この計画に含まれないアプリ本体の大きなリファクタリングは行わないこと。

## 6. 関連ドキュメント (Related Docs)
- 要件定義: [doc/plans/containerization-requirements.md](/Users/aoitan/workspace/kuroko/issue-19/doc/plans/containerization-requirements.md)
- Issue: #29 `開発環境と実行環境のコンテナ化`
