# Implementation Plan - Issue #22: ルールベースによるTODO/期限等の抽出

## 1. 目的
LLM を使用せず、正規表現ベースでメモのチャンクから TODO、期限、pending、会議、比較検討の候補を抽出し、DB（`inferences` テーブル）に保存する。これにより、軽量な意味付けを自動化し、後続の `shinko` (LLM層) や UI でのフィルタリングに利用可能にする。

## 2. スコープ
- **DBスキーマ拡張**: `inferences` テーブルの新規作成。
- **抽出エンジン (`InferenceEngine`)**:
    - カテゴリ（TODO, DEADLINE, PENDING, MEETING, COMPARE）ごとの正規表現ルールの定義。
    - チャンクの `block_timestamp` を基準とした相対日付（明日、来週など）の簡易的な絶対日時変換。
    - 抽出結果（推論タイプ、内容、メタデータ）の構造化。
- **収集フローへの統合**: `kuroko collect memo` 実行時に、新規または更新されたチャンクに対して自動的に抽出を実行する。
- **再抽出コマンドの提供**: 既存の全チャンクに対してルールを再適用する `--re-inference` オプションの追加。

## 3. 非スコープ
- 形態素解析器（MeCab, Spacy 等）の導入。
- 100% の抽出精度保証（「候補」として扱う）。
- 抽出結果に基づく自動的なアクション（通知など）。

## 4. タスク一覧

### 4.1. DBスキーマの更新 (`kuroko_core/db.py`)
- [x] `inferences` テーブルを作成する。
- [x] `chunk_id` と `inference_type` に対するインデックスを作成。

### 4.2. 抽出エンジンの実装 (`kuroko/inference.py`)
- [x] `InferenceEngine` クラスを作成。
- [x] カテゴリごとの正規表現パターンを定義（メンテナンス性を考慮し、リスト形式で管理）。
- [x] 相対日付表現の簡易パース機能を実装（`明日` -> 基準日+1日 など）。
- [x] `extract(chunk_text, base_date)` メソッドの実装。

### 4.3. 収集フローへの統合 (`kuroko/memo_collector.py`)
- [x] `save_chunks` の戻り値（`changed_chunk_ids`）を利用して、変更があったチャンクに対して `InferenceEngine` を実行する。
- [x] 抽出結果を `inferences` テーブルに保存（既存の `inference` は一旦削除して再登録）。

### 4.4. CLIオプションの追加 (`kuroko/cli.py`, `kuroko/memo_collector.py`)
- [x] `kuroko collect memo` に `--re-inference` フラグを追加。
- [x] 全 `chunks` を走査して `inferences` を再生成する `re_inference_all(db_conn)` 関数を実装。

### 4.5. テストの実装 (`tests/test_inference.py`)
- [x] 各カテゴリの抽出パターンがプロトタイプの期待値（02-prototype-summary.md）を満たすことを確認。
- [x] 相対日付が基準日に基づいて正しく解決されるかを確認。
- [x] DB への保存・読み出しが正しく行われるかを確認。


## 5. タスク依存関係
1. DBスキーマ変更 (4.1)
2. 抽出エンジンの実装 (4.2) & 単体テスト (4.5)
3. 収集フローへの統合 (4.3)
4. CLIオプション追加 (4.4)

## 6. 実装順序
1. **4.1**: DBテーブルの準備。
2. **4.2**: ロジックの中核を実装。
3. **4.5**: ロジックの正当性を担保.
4. **4.3**: 既存機能への組み込み。
5. **4.4**: 運用利便性の向上。

## 7. チェック方法
- `pytest tests/test_inference.py` が全件パスすること。
- サンプル `memo.md` を用意し、`kuroko collect memo` 実行後に SQLite DB を直接開き、`inferences` テーブルに期待通りのレコードが入っていることを確認する。
- `kuroko collect memo --re-inference` を実行し、既存の推論結果が更新されることを確認する。

## 8. リスク対応
- **ReDoS 対策**: 正規表現をシンプルに保ち、ネストされた繰り返し（例: `(a+)+`）を避ける。チャンク単位での処理のため入力長は限定的だが、念のため正規表現の実行にタイムアウト（Python標準では難しいため、構造を単純にする）を意識する。
- **日付の曖昧性**: `inferences.metadata` に必ず `base_date` (抽出時の基準日) を保存し、後から「いつの明日か」を追跡可能にする。
- **ノイズ検知**: 最初は保守的なパターンから始め、テストケースを増やしながら精度を調整する。

## 9. 実装担当への申し送り
- `InferenceEngine` はステートレスに設計し、基準日を引数で受け取るようにしてください。
- 正規表現パターンには、それぞれ何にマッチさせる意図かコメントを付与してください。
- DB への保存時は、`chunk_id` ごとに一度 `DELETE` してから `INSERT` する「洗い替え」方式が、実装の単純化と不整合防止に役立ちます。
- `block_timestamp` は ISO 形式の文字列で保存されているため、`datetime.fromisoformat` でパースして計算に用いてください。
