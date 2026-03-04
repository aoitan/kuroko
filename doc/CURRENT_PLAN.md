# Implementation Plan: `kanpe` UI への Worklist 統合とレイアウト刷新

## 1. 概要とゴール (Summary & Goal)
`kanpe` デッシュボード上で、プロジェクトの作業証跡（Report）と GitHub の課題状態（Worklist）を同時に閲覧可能にし、さらに UI 上のボタンからそれらを最新化できるようにする。

- **Must**:
  - `kuroko report` コマンドへの `--include-worklist` オプションの追加。
  - レポート内に 「Worklist」セクション（PR/Issue のテーブル表示）を追加。
  - `kanpe` UI への「Refresh」ボタンの設置。
  - ボタン押下時にサーバー側で `kuroko report` を再実行し、画面をリロードする機能。
- **Want**:
  - `kanpe` UI のレイアウト調整（固定ヘッダー、セクション間のナビゲーション等）。
  - リフレッシュ中のローディング表示。

## 2. スコープ定義 (Scope Definition)
### ✅ In-Scope (やること)
- `kuroko/reporter.py`: `generate_report` を拡張し、Worklist データのレンダリングをサポート。
- `kuroko/cli.py`: `report` サブコマンドに `--include-worklist` オプションを追加し、`worklist` 取得ロジックを統合。
- `kanpe/cli.py`: 
  - `HTML_TEMPLATE` を更新してリフレッシュボタンと JavaScript を追加。
  - `BaseHTTPRequestHandler` にリフレッシュ実行用のパス（`/refresh`）を追加。
  - リフレッシュ実行時に `refresh_report` 関数を呼び出す。

### ⛔ Non-Goals (やらないこと/スコープ外)
- Worklist の詳細なソート・フィルタリング（既存の `worklist` コマンドの機能を踏襲する）。
- ブラウザ側でのリアルタイム自動更新（手動ボタンのみとする）。

## 3. 実装ステップ (Implementation Steps)
1. [ ] **Step 1: Reporter の拡張**
   - *Action*: `kuroko/reporter.py` の `generate_report` に `worklists` 引数を追加し、Markdown の新セクションとして描画。
2. [ ] **Step 2: `kuroko report` の強化**
   - *Action*: `kuroko/cli.py` の `report` コマンドで `--include-worklist` フラグを処理し、各プロジェクトのリポジトリからデータを取得して Reporter に渡す。
   - *Validation*: `kuroko report --include-worklist output.md` で Worklist を含むレポートが生成されることを確認。
4. [ ] **Step 4: `kanpe` UI へのボタン追加**
   - *Action*: `kanpe/cli.py` の `HTML_TEMPLATE` を修正し、右上に POST 送信用の「Refresh & Reload」ボタンを配置。CSRF 対策のための nonce を含める。
5. [ ] **Step 5: サーバー側リフレッシュ処理の実装**
   - *Action*: `kanpe/cli.py` の `Handler` で `/refresh` への **POST リクエストのみ**を受け付けるエンドポイントを実装。nonce を検証した上で `refresh_report` を実行後、303 リダイレクトでトップページへ戻す。
   - *Validation*: UI のボタン押下によりレポートが再生成され、画面が更新されることを確認。GET リクエストが拒否されることを確認。

## 4. 検証プラン (Verification Plan)
- `kuroko report --include-worklist` で生成された Markdown ファイルを直接確認。
- `kanpe --refresh` で起動し、ブラウザ上のボタンから最新の証跡と PR リストが反映されることを確認。

## 5. ガードレール (Guardrails for Coding Agent)
- `kuroko report` の既存の動作（Worklist を含まない場合）を壊さないこと。
- `bleach` によるサニタイズ設定を維持し、追加される HTML 要素も安全に扱うこと。
