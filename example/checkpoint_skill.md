---
name: checkpoint
description: 作業の進捗・根拠・詰まりをタイムライン形式でチェックポイントファイルに追記する
---

# 目的

- 作業の「何をしたか」と「根拠」と「詰まり」を、あとで追える形で残す。
- 未来の自分／秘書LLMが「最後なにしてた？」「どこで詰まってる？」を即答できる状態にする。

# 入力（ユーザー要求から抽出）

- project: プロジェクト名（repo名推奨）
- issue: Issue番号（任意。無い場合は `misc`）
- phase: `planning` / `coding` / `review` / `fix` / `closing`
- act: やったこと（1文）
- evd: 根拠（ログ1行、コマンド、差分、リンク、コミット、ファイル位置など。可能なら必須）
- block: 詰まり（無ければ `なし` でよい）

# 出力ファイル仕様

## ファイル名

- Issueあり: `YYYY-MM-DD__{project}__ISSUE-{number}.md`
- Issueなし: `YYYY-MM-DD__{project}__misc.md`

例:
- `2026-02-28__multi-llm-agent-cli__ISSUE-123.md`
- `2026-02-28__vocal_insight_ai__misc.md`

## 保存場所（推奨）

- リポジトリ直下の `checkpoint/` ディレクトリ
  - 例: `checkpoint/2026-02-28__...md`

※ 既存運用があるならそれに従う。

# タイムライン形式（追記ルール）

- ファイル先頭に `# Timeline` が無ければ作成する。
- 末尾にエントリを追記する（上書きしない）。
- 1エントリは **Timestamp / Phase / Action / Evidence / Blocker** のみ。

## エントリテンプレ

```md
- HH:MM [phase] act: <やったこと>
  evd: <根拠>
  block: <詰まり or なし>
```

# Evidence（根拠）の例

- コマンド: `git status`, `git diff --stat`, `pytest -q`, `npm test`
- 差分/位置: `src/foo.ts:L120-180`
- コミット: `commit: abc1234`
- PR/Issue: `PR #12`, `ISSUE-123`
- ログ1行: `ERROR: ...`
- 参考リンク（貼れる範囲で）

# Blocker（詰まり）の例

- `block: 再現条件が不明（どの入力で落ちる？）`
- `block: 期待仕様が未確定（A/Bどっち？）`
- `block: 権限/鍵/環境がない（Xにアクセスできない）`
- `block: 依存が壊れてる（version conflict）`
- `block: なし`

# 実行手順（このスキルの振る舞い）

1. 現在時刻を確認する（ホスト環境のコマンドを使用する）
   - Mac/Linuxの場合: `date "+%Y-%m-%d %H:%M:%S"` を実行
   - Windows (PowerShell)の場合: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"` を実行
2. ユーザー要求から `project / issue / phase / act / evd / block` を埋める。
3. ファイル名を規則に従って決める（Issue無ければ `misc`）。
4. `checkpoint/` 配下にファイルが無ければ作成する。
5. `# Timeline` が無ければ先頭に追加する。
6. 現在時刻（ローカル）でエントリを生成し、末尾に追記する。
7. 追記後、ユーザーに以下を簡潔に報告する:
   - 追記したファイルパス
   - 追記した1エントリ（そのまま）

# ガードレール（重要）

- 不明なことは埋めない。`evd` が無いなら「取れていない」と書く。
- `phase` は必ず上の5種類のどれかに丸める（新しい種類を勝手に増やさない）。
- `act` は1文で。長文の説明は別メモに分離し、ここにはリンクだけ置く。

# 例

```md
# Timeline

- 03:12 [coding] act: checkpointスキル用のタイムラインテンプレを追加
  evd: git diff --stat
  block: なし

- 03:40 [fix] act: pytestが落ちる原因を調査して依存の競合を確認
  evd: ERROR: ImportError: ...
  block: 依存が壊れてる（version conflict）
```
