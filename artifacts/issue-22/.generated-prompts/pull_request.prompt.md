# Context

Issue Number: 22
Issue Source: github
GitHub Repo: aoitan/kuroko
Working Directory: /Users/aoitan/workspace/kuroko/issue-22
Current Phase: pull_request

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

# pull request prompt

あなたはPRドラフト作成担当です。

必ず以下を守ってください。

- PR本文では GitHub Issue との対応関係が人間に伝わるようにする
- `AGENTS.md` と `skills/pull-request/SKILL.md` に従う
- 人間レビューしやすさを最優先にする
- 実装全体を要約し、どこを重点的に見ればよいか示す
- 最後に成果物 `artifacts/issue-22/07-pr-draft.md` を更新する

出力に必ず含める項目:

1. タイトル案
2. 背景
3. 変更概要
4. 主な変更点
5. テスト / 確認
6. 既知の制約
7. レビューポイント
8. ロールバック観点



# Phase Skill

---
name: pull-request
description: Prepare a pull request summary with background, change overview, validation results, constraints, and review focus points.
---

# SKILL: pull request

## 目的
人間レビューに必要な背景・差分・確認結果・注意点を整理する。

## この工程で重視すること
- レビューしやすさ
- 背景の十分性
- 変更範囲の要約
- 注意点の明示

## 手順
1. 変更背景を要約する
2. 何を変えたかまとめる
3. テストや確認結果を書く
4. 残制約を書く
5. 重点レビューポイントを示す

## 避けること
- 差分説明のないPR文
- テスト情報の欠落
- 注意点の隠蔽

## 成果物チェック
- 背景と変更点が区別されているか
- テストがあるか
- レビューポイントがあるか
- 既知制約が書かれているか



# Previous Artifacts

(none)

# Execution Notes

- Work inside the repository at: /Users/aoitan/workspace/kuroko/issue-22
- Update files directly when appropriate.
- Prefer small, reviewable diffs.
- Leave explicit notes when blocked or uncertain.
