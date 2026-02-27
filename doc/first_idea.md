# 秘書スクリプトを作りたい
## 秘書スクリプトの最小ゴール

* workspace 配下の `**/checkpoint/*.md` を拾う（git管理外でもOK）
* **最新N件**を時系列で並べて
* 「最後に何してた？」「どこで詰まってる？」を出す

## 仕様

### 設定ファイル（例：secretary.config.yaml）

* 読みたいrepoルートのフルパスを並べる
* ついでにプロジェクト表示名も持てるように

```yaml
version: 1
projects:
  - name: multi-llm-agent-cli
    root: /abs/path/to/workspace/multi-llm-agent-cli
  - name: vocal_insight_ai
    root: /abs/path/to/workspace/vocal_insight_ai
defaults:
  per_project_files: 5
  checkpoint_dir: checkpoint
  filename_glob: "*.md"
```

### 収集ルール

* 各 root/{checkpoint_dir}/*.md を対象
* ファイル名の YYYY-MM-DD__... を基本に 新しい順
* うまくパースできないファイルが混ざっても、mtimeでフォールバック
* 各プロジェクト最大per_project_filesファイルを読み込む

### 入力

* `--issue 123`（任意：`ISSUE-123` でフィルタ）
* `--phase coding,fix`（任意）

### 出力（人間用）

1. **Latest activity**（各プロジェクトの最新1件）
2. **Active blockers**（block: なし以外の最新順）
3. **Timeline**（直近N件をそのまま）

例：

* `multi-llm-agent-cli / ISSUE-123: 03:40 [fix] …`
* `BLOCK: 依存が壊れてる（version conflict） @ vocal_insight_ai …`

### 出力（LLM用JSON）

秘書LLMに投げるなら、まずこれで十分：

```json
{
  "generated_at": "2026-02-28T03:55:00+09:00",
  "items": [
    {
      "project": "multi-llm-agent-cli",
      "issue": "123",
      "date": "2026-02-28",
      "time": "03:40",
      "phase": "fix",
      "act": "...",
      "evd": "...",
      "block": "..."
    }
  ]
}
```

## パーサ設計

* example/checkpoint_skill.mdで定義されている出力フォーマットをパースしたい
* 1行目：`- HH:MM [phase] act: ...`
* 次行以降：`evd:` と `block:` を探す（順不同でもOK）
* 欠けてても落とさず `null` 扱い

## 実装方針

* 言語：Python でいい（glob + regex）
* 検索：`root/**/checkpoint/*.md`（深さ無制限）
* 並び：ファイル名の日付 + `HH:MM` をキーにソート
* “block: なし” は blocker 集計から除外（`なし`, `none`, `n/a` くらい許容）

## まず作るコマンド（使い勝手）

* `secretary recent` : 直近N件
* `secretary blockers` : blockerだけ
* `secretary status` : 各projectの最新1件

