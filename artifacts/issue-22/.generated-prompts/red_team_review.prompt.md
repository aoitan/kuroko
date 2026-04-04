# Context

Issue Number: 22
Issue Source: github
GitHub Repo: aoitan/kuroko
Working Directory: /Users/aoitan/workspace/kuroko/issue-22
Current Phase: red_team_review

# Issue

# GitHub Issue #22: Phase 5: ルールベースによるTODO/期限等の抽出

- Repository: aoitan/kuroko
- URL: https://github.com/aoitan/kuroko/issues/22
- State: OPEN
- Author: aoitan

## Body

## 背景
Epic #16 の第2段階として、LLM に頼らず軽い意味づけを自動化する。

## 目的
- memo/chunk から TODO・期限・pending などの候補を機械的に抽出する
- shinko の前処理として使えるルールベース層を用意する

## 要件
- TODO候補 / 期限候補 / pending候補 / 会議・調整候補 / 比較検討候補を抽出対象にする
- 明日・今週・◯日まで、やる・確認・送る、待ち・返信待ち などの語を最低限拾えること
- inference 候補テーブルなど再利用しやすい形で保持できること

## 完了条件
- LLM なしでも候補抽出結果を後続処理で再利用できること

Related: #16


# AGENTS.md

# AGENTS.md

このリポジトリでは、CLIエージェントに「1工程ずつ」仕事をさせる。

目的は、単発の巨大プロンプトで全部やらせるのではなく、
以下の工程を順番に実行し、各工程の成果物を明示的に残すこと。

1. prototype planning
2. prototyping
3. red team review
4. planning
5. implementation
6. review/fix loop
7. pull request

---

## 基本ルール

- 常に **Issue #xx** を起点に作業する。
- Issue の主ソースは **GitHub Issues** を優先する。
- 必要に応じて Issue コメントも入力に含める。
- 1回の工程では **その工程の責務だけ** を実施する。
- 次工程に必要な情報は、必ず成果物として `artifacts/` に残す。
- 不明点があっても作業停止を最小化し、妥当な仮定を明示して前進する。
- 破壊的変更・依存追加・権限変更・外部送信を伴う場合は理由を成果物に記録する。
- 実装より前に、少なくとも一度は失敗条件・非目標・既知リスクを書く。
- 各工程では、対応する `skills/<phase>/SKILL.md` を必ず読む前提で行動する。
- 各工程終了時に、最低限以下を出力する:
  - 何をやったか
  - 何をやっていないか
  - 次工程への入力
  - リスク / 未解決事項

---

## ディレクトリ規約

```text
artifacts/
  issue-xx/
    01-prototype-planning.md
    02-prototype-summary.md
    03-red-team-review.md
    04-plan.md
    05-implementation-notes.md
    06-review-fix-loop.md
    07-pr-draft.md
    .issue-cache/
      issue.json
      issue_comments.json
    intent-records/
    checks/
```

`artifacts/issue-xx/` 配下に工程ごとの成果物を残す。

---

## 工程ごとの責務

### 1) prototype planning
目的:
- 問題の理解を揃える
- 最小プロトタイプの範囲を決める
- 成否判定を簡単に定義する

出力:
- `01-prototype-planning.md`

やること:
- GitHub Issue を要約
- 要件 / 非要件 / 仮定 / リスク整理
- 最小スパイク案を 1〜3 個提案
- 最初に作る試作品を 1 つに絞る
- 何を捨てるか明記

### 2) prototyping
目的:
- 捨てやすい実験で見通しを得る

出力:
- `02-prototype-summary.md`
- 必要なら試作コード

やること:
- 本実装前提にせず、最短で仮説検証
- 設計の美しさより学習速度を優先
- 試したこと / わかったこと / 無理だったことを記録

### 3) red team review
目的:
- 試作や計画の危険点を先に炙る

出力:
- `03-red-team-review.md`

やること:
- 想定破綻点、誤用、過信、見落としを列挙
- 仕様の穴、セキュリティ、運用事故、UX事故、保守性を点検
- 「このまま進めるなら最低限必要なガード」を提案

### 4) planning
目的:
- 実装可能な計画に落とす

出力:
- `04-plan.md`

やること:
- タスク分解
- 依存関係整理
- 実装順序決定
- 完了条件と確認方法の明記

### 5) implementation
目的:
- 計画に従って実装する

出力:
- コード変更
- `05-implementation-notes.md`

やること:
- 1回で全部盛りしない
- 計画との差分が出たら理由を書く
- 追加したファイル、主要変更点、未対応点を残す

### 6) review/fix loop
目的:
- 実装品質を上げる

出力:
- `06-review-fix-loop.md`

やること:
- レビュー
- 問題の優先度付け
- 修正
- 再確認
- ループを定義回数または収束条件まで回す

### 7) pull request
目的:
- 人間がレビューしやすいPR材料を揃える

出力:
- `07-pr-draft.md`

やること:
- 変更概要
- 背景
- 変更点
- テスト
- 残課題
- レビューポイント

---

## エージェントへの共通指示

- 大きく迷ったら、抽象議論を伸ばしすぎず、現時点で妥当な選択肢を1つ採る。
- 不確実性は消さずに記録する。
- できるだけ小さい差分を積む。
- GitHub Issue 本文とコメントのうち、実装判断に効く文脈を優先して使う。
- Issue だけで足りない場合は、リポジトリ内の関連コード・既存ドキュメント・過去成果物で補完する。
- 自動チェック可能な点は常に意識する。
- 将来 `Intent Record` と `機械チェック` が差し込まれる前提で、判断理由を工程単位で残す。

---

## 各工程で参照する入力

- GitHub Issue 本文
- 必要に応じて GitHub Issue コメント
- `AGENTS.md`
- 対応工程の `skills/<phase>/SKILL.md`
- 対応工程の `prompts/*.md`
- それ以前の工程で生成された `artifacts/issue-xx/*`

---

## 失敗時の扱い

- 失敗を隠さない。
- 途中で詰まった場合も、
  - どこまで進んだか
  - 何が障害か
  - 次に人間が判断すべき点
  を成果物に残して終了する。


# Phase Prompt

# red team review prompt

あなたはレッドチームレビュー担当です。

必ず以下を守ってください。

- GitHub Issue に書かれた期待と実際の試作内容のズレも点検する
- `AGENTS.md` と `skills/red-team-review/SKILL.md` に従う
- 実装を褒めるのではなく壊す観点で見る
- 見つけた懸念は重大度と起こり方を書く
- 不確実でも、事故になりうるものは候補として挙げる
- 最後に成果物 `artifacts/issue-22/03-red-team-review.md` を更新する

出力に必ず含める項目:

1. 対象
2. 前提
3. 主要な懸念点一覧
4. 各懸念の重大度 / 発生条件 / 影響
5. 進行を止めるべき論点
6. 最低限必要なガード
7. planning工程へ反映すべき修正



# Phase Skill

---
name: red-team-review
description: Review a design, prototype, or plan from a failure-focused perspective and surface concrete risks, impacts, and minimum safeguards.
---

# SKILL: red team review

## 目的
設計・試作・計画の危険点を事前に洗い出し、事故コストを下げる。

## この工程で重視すること
- 悪用可能性
- 想定外入力
- 誤解を生むUX
- セキュリティ / 安定性 / 運用性
- 保守性

## 手順
1. 何が壊れると痛いか考える
2. どう壊れるかを具体化する
3. 影響範囲を見積もる
4. 最低限必要なガードを提案する
5. planning に反映すべき項目へ落とす

## 避けること
- 表面的な褒めレビュー
- 重大度の区別がない列挙
- 対策なしの不安喚起

## 成果物チェック
- 懸念ごとに発生条件があるか
- 重大度が書かれているか
- 最低限のガードが提案されているか
- 次工程へ反映可能な粒度か



# Previous Artifacts

## 01-prototype-planning.md

# Prototype Planning - Issue #22: ルールベースによるTODO/期限等の抽出

## 1. Issue理解の要約
LLMを使用せずに、正規表現やキーワードマッチングによるルールベースで、収集されたメモのチャンクからTODO、期限、pending、会議、比較検討などの属性を抽出し、DBに保存する仕組みを構築する。これは shinko（LLM層）の前処理としても機能し、軽量な意味付けを自動化することを目的とする。

## 2. 目的
- チャンクから特定の属性（TODO, 期限, pending, 会議, 比較検討）をルールベースで抽出する。
- 抽出結果をDB（新設する `inferences` テーブル）に保存し、再利用可能にする。
- LLMを介さず高速に動作し、shinko 等の後続プロセスにヒントを提供する。

## 3. 非目的
- LLMによる高度な文脈理解や意味解析（これは Phase 6 以降の責務）。
- 100%の抽出精度（ルールベースによる「候補（Candidate）」の抽出に留める）。
- 複雑な自然言語処理ライブラリの導入（標準ライブラリ re を優先）。

## 4. 仮定
- 抽出対象は `chunks` テーブルに保存された `chunk_text` である。
- 入力テキストは主に日本語を想定する。
- 抽出ルールは re モジュールによるパターンマッチングで定義可能である。

## 5. リスク
- **ノイズの混入**: 単純なキーワードマッチでは、意図しない箇所が TODO や期限として抽出される可能性がある。
- **ルールの競合**: 1つのチャンクが複数の属性を持つ場合の優先順位や重複扱いの決定が必要。
- **パターンの維持**: 抽出対象が増えるにつれて、正規表現が複雑化しメンテナンスが困難になる。

## 6. 候補プロトタイプ案
- **案A: スタンドアロンな抽出スクリプト**: 既存のDBを読み込み、ルールを適用して結果を表示するだけの最小限の検証。
- **案B: 抽出エンジン + DBスキーマ拡張**: 正規表現パターンのコレクションを持ち、抽出結果を `inferences` テーブルに保存する。
- **案C: Collector 統合プロトタイプ**: `collect_memo` の処理フローに組み込み、メモ収集と同時に抽出を行う。

## 7. 採用する案と理由
**案Bおよび案Cの統合案**を採用する。
- **理由**: 抽出結果をDBに保存しなければ後続の `shinko` 等で利用できず、また収集フローと統合することで実運用に近い形での検証が可能になるため。

## 8. 成否判定
- 以下のパターンを含むテスト用 `memo.md` から、意図した属性が正しく抽出されること。
    - TODO: 「〜を確認する」「〜を送る」
    - 期限: 「明日まで」「4/10」「来週中に」
    - pending: 「返信待ち」「確認中」
- 抽出結果が `inferences` テーブルに `chunk_id` と紐付いて保存されていること。

## 9. 次工程への入力
- `inferences` テーブルのスキーマ定義案。
- 抽出対象とするキーワード・正規表現パターンの初期リスト。
- `kuroko/inference.py` (仮) のクラス設計。


## 02-prototype-summary.md

# Prototype Summary - Issue #22: ルールベースによるTODO/期限等の抽出

## 1. 実験したこと
- 正規表現を用いたルールベースの抽出エンジン（`InferenceEngine`）の試作。
- TODO、期限、pending、会議、比較検討の5カテゴリに対するキーワードマッチングの検証。
- 抽出結果を SQLite DB の `inferences` テーブルに保存する一連の流れの確認。

## 2. 実装または検証内容
- `InferenceEngine` クラスを実装し、複数の正規表現パターンを順次適用して候補を抽出。
- 以下のサンプルテキストを用いて、意図した通りに抽出されるかを確認：
    - 「4/10までにレポートを送る。」
    - 「来週の会議の日程を調整する。案1: 月曜, 案2: 火曜」
    - 「クライアントからの返信待ち。保留中。」
    - 「TODO: [ ] デザイン案を検討する」
    - 「期限：明日まで。重要課題の修正を実装する。」

## 3. 観測結果
- 全てのサンプルケースで、少なくとも1つのカテゴリが正しく抽出された。
- 1つのチャンクから複数のカテゴリ（例：TODOと期限、MEETINGと比較検討）が同時に抽出できることを確認。
- 「検討する」が TODO と 比較検討（COMPARE）の両方にヒットするなど、重複抽出が発生するが、これは「候補」としての役割から許容範囲内である。
- 単純なキーワードマッチでは「送る」などの動詞が正しく拾えない場合があり、正規表現の微調整が必要（例：サ変名詞+「する」と、単独の動詞の区別）。

## 4. 使えそうな方針
- **正規表現の整理**: `re.IGNORECASE` の活用や、日本語特有の表記揺れ（全角・半角、送り仮名）への対応。
- **メタデータ抽出**: 期限カテゴリにおいて、日付部分（例：「4/10」「明日」）をメタデータとして JSON 形式で保存する仕組み。
- **DB統合**: `kuroko_core/db.py` に `inferences` テーブルを追加し、`collect_memo` のタイミングで自動実行する。

## 5. 捨てる方針
- **複雑なNLPライブラリの導入**: 今回の要件（軽量・高速）では、正規表現のみで十分な精度が出せると判断したため、Mecab や Spacy 等の導入は見送る。
- **厳密な依存関係解析**: TODO とその対象を厳密に結びつける解析は、今回のルールベース層では行わず、後続の LLM 層に任せる。

## 6. 本実装へ持ち込むべき知見
- `inferences` テーブルのスキーマ: `id`, `chunk_id`, `inference_type`, `content`, `metadata`, `created_at`。
- 抽出パターンのリスト化と管理方法。
- `memo_collector.py` における `save_chunks` の直後に抽出処理を差し込むフロー。

## 7. 未解決事項
- 抽出精度の向上（ノイズをどこまで許容するか）。
- 日本語の日付表現（「明後日」「再来週」など）をどこまでカバーするか。
- 重複する抽出結果の優先順位付けが必要かどうか。


# Execution Notes

- Work inside the repository at: /Users/aoitan/workspace/kuroko/issue-22
- Update files directly when appropriate.
- Prefer small, reviewable diffs.
- Leave explicit notes when blocked or uncertain.
