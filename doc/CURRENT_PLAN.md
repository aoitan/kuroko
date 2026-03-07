# Implementation Plan: [PoC] kanpe LLM Suggestion Feature (#7)

## 1. 概要とゴール (Summary & Goal)
- **Must**: `kanpe` のブラウザ画面に「次の一手を提案」ボタンを追加し、OpenAI 互換 API（Ollama 等）経由で LLM からのアドバイスを表示する。
- **Want**: 提案内容の履歴保存、プロンプトのカスタマイズ機能（今回はスコープ外）。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- `kuroko/llm.py` (新規): OpenAI 互換 API クライアントの実装。
- `kuroko/config.py`: LLM 設定（`llm_url`, `llm_model` 等）の追加。
- `kanpe/cli.py`: 
    - HTML テンプレートにボタンと提案表示エリアを追加。
    - `/suggest` エンドポイントを実装し、非同期で LLM 提案を返す。
- プロンプトの設計: レポート内容（Status, Worklist, Blockers）を元にしたアドバイス生成。

### ⛔ Non-Goals (やらないこと/スコープ外)
- Ollama 本体のセットアップ。
- ストリーミング回答（今回は PoC なので一括返却で十分）。
- 複数の LLM プロバイダへの対応（OpenAI 互換に限定）。

## 3. 実装ステップ (Implementation Steps)
1. [ ] **Step 1**: `kuroko/config.py` に LLM 用の設定項目を追加する。
2. [ ] **Step 2**: `kuroko/llm.py` を新規作成し、OpenAI 互換 API へのリクエスト処理を実装する。
3. [ ] **Step 3**: `kanpe/cli.py` に `/suggest` エンドポイントを追加し、現在のレポートファイルを読み取って LLM に投げるロジックを実装する。
4. [ ] **Step 4**: `kanpe/cli.py` の HTML/JS を更新し、ボタン押下で提案を取得・表示できるようにする。

## 4. 検証プラン (Verification Plan)
- `pytest` で `kuroko/llm.py` の動作確認（モック使用）。
- `kanpe --refresh` で起動し、実際に「次の一手を提案」ボタンを押し、アドバイスが表示されることを確認する。

## 5. ガードレール (Guardrails for Coding Agent)
- `kuroko` コアロジックの破壊的変更は行わない。
- 既存の `Refresh` 機能を壊さないように注意する。
- 外部ライブラリ（`openai` 等）を追加せず、標準の `urllib` または既存の依存関係で実装する（依存を増やさないため）。
