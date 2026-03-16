# Implementation Plan: Phase 4: サブコマンドの責務分離 (collect/shinko/kanpe) #19

## 1. 概要とゴール (Summary & Goal)
現状のオンデマンド収集＋整形一体型のロジックを、「収集・分析・提示」の3つの責務に分離し、各サブコマンドが独立して実行可能な構造に再設計する。

- **Must**:
  - `kuroko` を収集（collect）専用とする。
  - `shinko` を分析（analyze/insight）専用とする。
  - `kanpe` を提示（present/report）専用とする。
  - 各コマンド間のデータ受け渡しをDB経由に整理する。
- **Want**:
  - `checkpoints` データのDB永続化（現在はオンデマンド）。
  - 各コマンドからの相互呼び出しの整理。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- `kuroko/cli.py` の再編
  - `recent`, `blockers`, `status`, `worklist`, `report` を削除（または各コマンドへ移動）。
  - `collect` サブコマンドを強化（`checkpoints` のDB保存機能追加）。
- `shinko/cli.py` の再編
  - `recent`, `blockers`, `status`, `worklist`, `insight` (既存) を実装。
- `kanpe/cli.py` の再編
  - `report` (既存の `kuroko report`), `view` (既存の Web UI) を実装。
- `kuroko/collector.py` の修正
  - DBへの保存ロジックを追加。
- 既存テストの修正と新規テストの追加。

### ⛔ Non-Goals (やらないこと/スコープ外)
- **リファクタリング**: 責務分離に関係のない内部ロジックの大幅な変更は行わない。
- **UI改善**: Web UIの見た目や機能の追加は行わない。
- **埋め込み（将来）**: ベクトル検索や埋め込みの実装は今回は行わない。

## 3. 実装ステップ (Implementation Steps)

### Step 1: `kuroko collect` の強化とDB永続化
1.  [ ] `kuroko/collector.py` に `save_checkpoints_to_db` 関数を追加。
    - `source_texts` と `chunks` テーブルを使用。
2.  [ ] `kuroko/cli.py` に `collect checkpoints` サブコマンドを追加。
3.  [ ] `tests/test_collector.py` にDB保存のテストを追加。

### Step 2: `shinko` への分析コマンドの移管
1.  [ ] `kuroko/cli.py` から `recent`, `blockers`, `status`, `worklist` のロジックを `shinko/cli.py` に移植。
    - ファイル直接参照から、DB参照への切り替え（可能な範囲で）。
2.  [ ] `shinko/cli.py` を `click.group` 構造に変更し、サブコマンド化。
    - `shinko recent`, `shinko blockers`, `shinko status`, `shinko worklist`, `shinko insight`。

### Step 3: `kanpe` への提示コマンドの移管
1.  [ ] `kuroko/cli.py` の `report` コマンドを `kanpe/cli.py` に移植。
    - `kanpe report` として実装。
2.  [ ] 既存のWeb UI起動を `kanpe view` (または引数なしのデフォルト) に整理。

### Step 4: `kuroko` CLIのクリーンアップ
1.  [ ] `kuroko/cli.py` から移管済みのコマンドを削除。
2.  [ ] `pyproject.toml` の `project.scripts` を確認。

## 4. 検証プラン (Verification Plan)
- `pytest` ですべてのテストが通過すること。
- 以下のコマンドが意図通り動作することを確認：
  - `kuroko collect checkpoints`
  - `shinko status`
  - `shinko recent`
  - `shinko insight --input-file report.md`
  - `kanpe report report.md`
  - `kanpe --input-file report.md` (Web UI起動)

## 5. ガードレール (Guardrails for Coding Agent)
- `kuroko_core` の共通ロジックを壊さないこと。
- DBのスキーマ変更が必要な場合は慎重に行うこと。
- 各コマンドの引数（options）の互換性を可能な限り維持すること。
