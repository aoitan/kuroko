# Implementation Plan: Phase 4: サブコマンドの責務分離 (collect/shinko/kanpe) (#19)

## 1. 概要とゴール (Summary & Goal)
- **Must**:
  - `collect` を収集・保存責務に寄せ、`kanpe` を人間向け表示、`shinko` を分析責務として整理する。
  - `kanpe` と `shinko` が `kuroko report` のような表示用 CLI に依存せず、共有ロジック経由で必要なデータを取得できる状態にする。
  - 既存利用者への破壊を最小化しつつ、今後の Phase 5-7 に進めるための依存方向を明確にする。
- **Want**:
  - `kuroko recent/blockers/status/worklist` まで完全に再編すること。
  - `shinko` の推論結果保存や `kanpe daily/weekly/project` などの新ビュー実装。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- `kuroko/cli.py` の責務を見直し、少なくとも「表示生成ロジック」を CLI 本体から分離する。
- 共有データ取得・共有レポート生成のためのアプリケーション層を追加または既存モジュールへ抽出する。
  - 候補: `kuroko/reporter.py` の整理、または新規の薄いサービスモジュール追加。
- `kanpe/cli.py` の `--refresh` を `kuroko report` の subprocess 依存から外し、共有ロジック呼び出しへ置き換える。
- `shinko/cli.py` が表示済み Markdown だけに縛られないよう、少なくとも共有データ取得層を経由できる形へ変更する。
  - 最小実装は「DB/raw/chunk を読むための入口を shared layer に用意し、`shinko` から利用可能にする」まで。
- 既存コマンド互換性の扱いを明確にする。
  - `kuroko report` は削除せず、必要なら shared layer を呼ぶ薄い互換ラッパに留める。
- 関連テストと README のコマンド説明を更新する。

### ⛔ Non-Goals (やらないこと/スコープ外)
- **新機能追加**: Phase 5 以降の TODO 抽出、推論保存、埋め込み更新、`kanpe daily/weekly/project` の新規ビュー実装。
- **全面リネーム**: 既存 CLI の全サブコマンドを一気に廃止・改名する作業。
- **大規模リファクタリング**: Issue 19 に直接関係しない parser / collector / DB の整理。
- **永続化設計拡張**: `shinko` の出力保存用テーブル追加や複雑なスキーマ変更。

## 3. 実装ステップ (Implementation Steps)
1. [ ] **Step 1**: 依存関係の切り出し
   - *Action*: `kuroko/cli.py` に埋まっている `report` 向けの入力収集・filter 正規化・worklist 取得処理を、CLI 非依存の共有関数へ抽出する。
   - *Action*: `kuroko/reporter.py` は Markdown を組み立てる純粋関数として維持し、CLI 固有処理を持たせない。
   - *Validation*: 共有関数単位のテスト、または既存 `tests/test_reporter.py` と新規 CLI テストで挙動が変わらないことを確認する。

2. [ ] **Step 2**: `kanpe` の refresh 経路を再配線
   - *Action*: `kanpe/cli.py` の `refresh_report()` から `kuroko report` subprocess 依存を外し、Step 1 の shared layer を直接呼ぶ。
   - *Action*: レポート再生成に必要な `--project`, `--issue`, `--since`, `--until`, `--include-worklist` などの引数受け渡し方針を整理する。
   - *Validation*: `tests/test_kanpe_refresh.py` と関連テストを更新し、`kanpe --refresh` が subprocess なしでも同じ成果物を生成できることを確認する。

3. [ ] **Step 3**: `shinko` の入力境界を整理
   - *Action*: `shinko/cli.py` の「`report.md` を丸ごと LLM に渡す」構造を見直し、shared layer から raw/chunk 系データを取得できる入口を追加する。
   - *Action*: 互換性のため、既存 `--input-file` を残す場合でも、内部では「表示データ」と「分析用データ」を切り分ける。
   - *Validation*: `tests/test_shinko_cli.py`, `tests/test_shinko_history.py`, `tests/test_shinko_sanitization.py` を更新し、モード指定・project 絞り込み・履歴付与が維持されることを確認する。

4. [ ] **Step 4**: `kuroko` 側の責務を収集寄りに寄せる
   - *Action*: `kuroko/cli.py` では `collect` を主責務として明確化し、`report` は互換ラッパまたは deprecation コメント付きの薄い導線に留める。
   - *Action*: `recent/blockers/status/worklist` を今回残すなら、その理由を README と計画上で明示し、「完全再編は別 Issue」に切り分ける。
   - *Validation*: `tests/test_cli_collect.py` と必要な CLI テストで既存コマンドが壊れていないことを確認する。

5. [ ] **Step 5**: ドキュメントと回帰確認
   - *Action*: `README.md` のコマンド説明を責務分離後の実態に合わせて更新する。
   - *Action*: 必要なら `doc/ROADMAP.md` と齟齬が出ないよう最小限の追記を行う。
   - *Validation*: `uv run pytest` を実行し、CLI・report・kanpe・shinko 系テストがすべて通ることを完了条件とする。

## 4. 検証プラン (Verification Plan)
- `uv run pytest tests/test_cli_collect.py tests/test_reporter.py tests/test_kanpe_refresh.py tests/test_kanpe_shinko_invocation.py tests/test_kanpe_suggest.py tests/test_shinko_cli.py tests/test_shinko_history.py tests/test_shinko_sanitization.py`
- 可能なら最終確認として `uv run pytest` 全体を実行する。
- 手動確認:
  - `kuroko collect memo` が従来どおり動くこと。
  - `kanpe --refresh --input-file report.md` でレポート再生成と表示ができること。
  - `shinko` が shared layer 経由の分析入力を使ってもモード別応答を返せること。

## 5. ガードレール (Guardrails for Coding Agent)
- 互換性を壊す CLI 削除は行わない。廃止したい場合はまず薄いラッパを残す。
- subprocess 呼び出しを減らす目的で、shared layer に寄せる。ただしロジック重複のまま別 CLI へコピーしない。
- `shinko` は Roadmap の通り「生寄り入力」に近づけるが、Issue 19 の範囲では推論保存や抽出器追加まで広げない。
- `kanpe` は表示責務に留め、分析ロジックや収集ロジックを抱え込まない。
- テストは CLI 文字列の表層だけでなく、依存方向が改善したことを確認できるように更新する。
