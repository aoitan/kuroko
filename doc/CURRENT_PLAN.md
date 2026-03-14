# Implementation Plan: llm提案機能に温度感を足す (kanpeの次の一手を提案ボタンを3種類に分ける)

## 1. 概要とゴール (Summary & Goal)
- **Must**: kanpeのWeb UIにある「次の一手を提案」機能を、ユーザーの状況に合わせた3つのモード（通常推薦、保守救済推薦、深掘り推薦）で実行できるようにする。
- **Must**: 対象とするプロジェクトを画面上のStatus表から抽出し、指定できるようにする。
- **Want**: 特になし（今回は必須要件のみに集中する）。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- **`shinko/cli.py`**:
    - `--mode` オプション（`normal`, `rescue`, `deep`）の追加。
    - `--project` オプションの追加。
    - `mode` および `project` の指定に応じたシステムプロンプトの出し分けロジックの実装。
- **`kanpe/cli.py`**:
    - Webサーバーの `/suggest` エンドポイントで `mode` と `project` パラメータを受け取る。
    - `invoke_shinko` 関数を修正し、受け取ったパラメータを `shinko` コマンド呼び出し時に渡す。
    - HTMLテンプレート（`HTML_TEMPLATE`）内のUI修正：
        - レポート内のテーブルからプロジェクト名を抽出し、プルダウンリストに設定するJavaScriptの追加。
        - 既存の「次の一手を提案」ボタンを廃止し、3種類のボタン（「🚀 通常」、「🧹 保守救済」、「🔍 深掘り」）とプロジェクト選択プルダウンを配置する。
        - `getSuggestion(mode)` 関数に修正し、選択されたプロジェクトとモードを POST パラメータとして送信する。
- **テストの追加・修正**:
    - `tests/test_kanpe_shinko_invocation.py` や `tests/test_kanpe_refresh.py` などの関連テストを、今回の引数追加・UI変更に合わせて更新する。

### ⛔ Non-Goals (やらないこと/スコープ外)
- **リファクタリング**: 今回の変更に関係のない箇所のコード整理は行わない。
- **追加機能**: LLMへのプロンプト以外の、`shinko` の根本的なLLM呼び出しロジックの変更。
- **依存関係**: 新しいライブラリの追加は行わない。

## 3. 実装ステップ (Implementation Steps)
1.  [ ] **Step 1**: `shinko/cli.py` の拡張
    - *Action*: `--mode` と `--project` 引数を追加。モードとプロジェクトに応じて `messages` の `system` コンテンツを動的に生成する。
2.  [ ] **Step 2**: `kanpe/cli.py` のサーバーサイド拡張
    - *Action*: `invoke_shinko` に `mode` と `project` 引数を追加。`/suggest` の `do_POST` で `parse_qs` を使ってパラメータを取得し渡すようにする。
3.  [ ] **Step 3**: `kanpe/cli.py` のフロントエンド（HTML/JS）拡張
    - *Action*: `HTML_TEMPLATE` を修正。テーブルからプロジェクト名を抽出し `<select>` に追加する初期化スクリプトを追加。ボタンを3つに増やし、`getSuggestion('normal')` のように呼ぶよう変更。
4.  [ ] **Step 4**: テストの更新
    - *Action*: 変更に合わせた既存テストの修正。`uv run pytest` を実行し、全てパスすることを確認。

## 4. 検証プラン (Verification Plan)
- `uv run pytest` が全て通ること。
- 手動確認: `kuroko report` を生成後、`kanpe` を起動。
    - プルダウンにテーブル内のプロジェクト（例: `kuroko`, `shinko` など）が表示されるか。
    - 3つのボタンをそれぞれクリックし、意図したモードとプロジェクトで提案が取得でき、画面に表示されるか。

## 5. ガードレール (Guardrails for Coding Agent)
- 既存のロジックを変更する場合は、必ずコメントで理由を残すこと。
- この計画に含まれないファイルの変更は禁止する。
