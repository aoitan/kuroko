# Kuroko Report

- generated_at: 2026-03-01T00:02:34.744306
- per_project_files: 5
- filters: none

## Status
| date | time | phase | project | issue | act |
|---|---:|---|---|---:|---|
| 2026-02-28 | 16:45 | code | deep_project | - | 深い階層のcheckpointテスト |
| 2026-02-28 | 17:15 | plan | kuroko | - | kuroko reportコマンドの実装計画を作成 |

## Blockers
- **[kuroko #1 | 2026-02-28 11:30 | code] 依存関係の解決に少し手間取った**
  <details><summary>details</summary>

  - act: parserとcollectorを実装
  - evd: `uv run pytest`

  </details>

## Recent
### 2026-02-28
- 17:15 plan kuroko - kuroko reportコマンドの実装計画を作成
- 17:00 done kuroko - READMEへのファイル形式およびLLMエージェント統合（スキル利用）の案内を追加
- 16:50 code kuroko - 検索範囲を深さ無制限(root/**/checkpoint/*.md)に変更し、max_depthオプションを追加
- 16:45 code deep_project - 深い階層のcheckpointテスト
- 16:30 done kuroko - グローバル設定（~/.config/kuroko/config.yaml）と絶対パスによる動作確認の完了
- 16:15 done kuroko - uv tool install --editable によるパッケージングと動作確認
- 15:55 done kuroko - checkpointディレクトリのGit管理除外
- 15:40 done kuroko - README of documentation and MIT License implementation
- 15:15 code kuroko - MVP実装（parser, collector, CLI）と設定ファイル探索ロジックの改善
- 11:30 code kuroko #1 parserとcollectorを実装
- 10:00 plan kuroko #1 kurokoの実装を開始
