# Implementation Plan: Containerization Requirements for Development and Runtime

## 1. 概要とゴール (Summary & Goal)
- **Must**: `kuroko` / `kanpe` / `shinko` を、issue ごとの `git worktree` を bind mount したコンテナで実行できるように設計する。
- **Must**: 開発中に環境や依存関係を壊しても、コンテナを破棄して再作成すればやり直せる構成にする。
- **Must**: 永続化すべき状態と破棄してよい状態を分離し、損切りプロトタイピングに耐える運用要件を明文化する。
- **Must**: 開発環境コンテナと実行環境コンテナの責務を分ける。
- **Want**: VS Code Dev Container 対応、将来の cron 実行対応、ビルドキャッシュ最適化。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- 開発環境コンテナの要件を定義する。
- 実行環境コンテナの要件を定義する。
- `git worktree` を bind mount する前提の運用要件を定義する。
- 「壊れたら捨ててやり直せる」ための状態分離方針を定義する。
- 設定ファイル、SQLite DB、レポート、checkpoint、キャッシュの保存方針を定義する。
- `docker compose` ベースの操作前提を定義する。
- 受け入れ条件と非機能要件を定義する。
- 想定追加ファイルを定義する。
  - `Dockerfile.dev`
  - `Dockerfile`
  - `compose.yaml`
  - `.dockerignore`
  - `README.md` または `doc/` 配下の運用説明

### ⛔ Non-Goals (やらないこと/スコープ外)
- **実装着手**: Dockerfile や compose の実装はこの文書では行わない。
- **オーケストレーション**: Kubernetes や本番クラスタ設計は行わない。
- **DB移行**: SQLite から Postgres や外部 Vector DB への移行は行わない。
- **本番監視**: observability、secrets 配布、運用監視基盤の詳細設計は行わない。
- **アプリ改修**: コンテナ化以外を目的とした広いリファクタリングは行わない。

## 3. 要件定義 (Requirements)
### 3.1 運用モデル
- 1 issue = 1 `git worktree` を基本単位とする。
- 各 worktree をコンテナ内の固定パス、例えば `/workspace` に bind mount する。
- コンテナは再作成可能であることを前提にし、壊れたら破棄して再作成できることを優先する。
- 損切りプロトタイピング時は「コンテナを捨てる」だけで環境を初期化できることを目標とする。

### 3.2 状態分離
- コンテナイメージは不変とし、開発中の可変状態は bind mount または volume に限定する。
- 永続化対象と破棄可能対象を明確に分ける。
- 永続化対象:
  - ソースコードを含む worktree
  - `kuroko.config.yaml` 相当の設定
  - SQLite DB
  - 生成した `report.md` や派生レポート
  - `checkpoint/` 入力
- 破棄可能対象:
  - コンテナ内部の一時ファイル
  - Python 実行環境の破損状態
  - 開発途中の依存関係の破損
  - 一時キャッシュ
- キャッシュは再生成可能であることを前提に、必要なら named volume に逃がす。

### 3.3 ディレクトリ方針
- worktree 直下にはソースと最小限の運用ファイルだけを置く。
- 実行生成物は `./.data` または `./var` のような明示ディレクトリに集約する。
- 少なくとも次の配置をサポートする。
  - `./.data/config.yaml`
  - `./.data/kuroko.db`
  - `./.data/report.md`
  - `./checkpoint/`
- コンテナ破棄後も再利用したいデータの置き場が、ソース変更と混在しないこと。

### 3.4 パス設計
- `projects[].root` はホスト絶対パスではなく、コンテナ内パスで完結することを前提とする。
- すべての CLI は、設定ファイルや DB パスを明示指定できることを前提に compose から起動する。
- カレントディレクトリ依存の暗黙解決を減らし、`-c/--config` と明示パス指定を基本運用とする。
- worktree bind mount 先は固定し、パス判定ロジックが環境差で壊れないようにする。

### 3.5 開発環境コンテナ要件
- `uv run pytest` がコンテナ内で再現できること。
- `uv run kuroko ...`、`uv run kanpe ...`、`uv run shinko ...` が実行できること。
- ソース変更は bind mount 経由でホストへ即時反映されること。
- non-root 実行を基本とし、bind mount 上の所有権を壊さないこと。
- 依存関係やツール追加で環境を壊しても、コンテナ再作成で復旧できること。
- 開発用キャッシュは named volume またはコンテナ内再生成可能領域に限定すること。

### 3.6 実行環境コンテナ要件
- `kuroko`、`kanpe`、`shinko` を個別 command として起動できること。
- `kanpe` は HTTP ポートを publish できること。
- 実行環境コンテナは開発ツール一式を必須としないこと。
- 実行に必要な設定、DB、入力、出力のみを mount すれば動作すること。
- 長時間プロセスが壊れても、コンテナ再起動または再作成で復旧できること。

### 3.7 再作成性 (Disposable / Recoverable)
- 開発コンテナは「壊しても捨ててやり直せる」ことを明示要件とする。
- やり直し時の手順は、コンテナ再 build または再 create のみで完結すること。
- やり直し時に失われてよいものと、保持すべきものが文書化されていること。
- プロトタイピング失敗時に、worktree と永続データを維持したまま環境だけ初期化できること。

### 3.8 操作要件
- `docker compose` で dev と runtime を統一操作できること。
- 典型操作は次で表現できること。
  - テスト実行
  - `kuroko` の収集処理実行
  - `shinko insight` 実行
  - `kanpe` 起動
  - 開発コンテナの破棄と再作成
- issue ごとの worktree に対し、同一 compose 定義を流用できること。

## 4. 実装ステップ (Implementation Steps)
1. [ ] **Step 1**: 運用モデルを固定する
   - *Action*: issue ごとの `git worktree` bind mount と `/workspace` 固定マウント前提を確定する。
   - *Validation*: どの worktree でも同じ compose 操作で起動できる前提が説明できること。
2. [ ] **Step 2**: 状態分離ポリシーを固める
   - *Action*: worktree、`.data`、キャッシュ、コンテナ内一時領域の責務を切り分ける。
   - *Validation*: 「捨ててよいもの」と「残すべきもの」が曖昧でないこと。
3. [ ] **Step 3**: 開発環境コンテナ要件を固める
   - *Action*: Python/uv/pytest、bind mount、non-root、キャッシュ方針を定義する。
   - *Validation*: 開発コンテナを壊した場合の復旧手順が compose 操作だけで説明できること。
4. [ ] **Step 4**: 実行環境コンテナ要件を固める
   - *Action*: `kuroko` / `kanpe` / `shinko` の起動責務と mount 要件を整理する。
   - *Validation*: 最小実行要件が開発環境と分離されていること。
5. [ ] **Step 5**: 受け入れ条件とドキュメント更新項目を固める
   - *Action*: compose 操作例と再作成性の確認項目を定義する。
   - *Validation*: コンテナ化実装後の完了判定基準が明確になっていること。

## 5. 検証プラン (Verification Plan)
- `docker compose run --rm dev uv run pytest` が通ること。
- `docker compose run --rm app kuroko collect memo --config /workspace/.data/config.yaml` が通ること。
- `docker compose run --rm app shinko insight --config /workspace/.data/config.yaml --input-file /workspace/.data/report.md` が通ること。
- `docker compose up kanpe` で Web UI を開けること。
- 開発コンテナを削除して再作成しても、worktree と `.data` の内容が保持されること。
- 故意にコンテナ内依存関係を壊した後でも、再作成で復旧できること。

## 6. ガードレール (Guardrails for Coding Agent)
- コンテナ化設計は「使い捨て可能だが、成果物は失わない」方針を崩さないこと。
- ホスト絶対パスを前提にした設定例を標準にしないこと。
- worktree 直下へ生成物を散在させないこと。
- 開発環境と実行環境の責務を混ぜないこと。
- 再作成不能なローカル状態をコンテナ内部に持ち込まないこと。
