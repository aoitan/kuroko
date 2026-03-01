# kuroko

各リポジトリに散らばる「証跡（checkpoint）」を収集・可視化するためのCLIツールです。
複数のプロジェクトの進捗や、現在発生しているブロック（詰まり）を一目で把握することを目的としています。

## 主な機能

- **証跡の収集**: 各プロジェクトの `checkpoint/` ディレクトリ配下にあるMarkdownファイルを収集します。
- **タイムライン表示**: 直近の作業内容を時系列で表示します。
- **ブロッカー表示**: 解決していない課題（block）を抽出して表示します。
- **ステータス確認**: 各プロジェクトの最新の活動状況を表示します。
- **LLMフレンドリー**: JSON形式での出力に対応しており、LLMエージェントへのインプットとして利用可能です。

## インストール（開発用）

`uv` を使用して実行することを推奨します。

```bash
git clone https://github.com/aoitan/kuroko.git
cd kuroko
uv tool install --editable .
```

## 使い方

### 証跡（checkpoint）の作成

kurokoは、各プロジェクトの `checkpoint/` ディレクトリ配下にある特定の形式のMarkdownファイルを読み込みます。

#### ファイル命名規則
- `YYYY-MM-DD__{project_name}__ISSUE-{number}.md`
- `YYYY-MM-DD__{project_name}__misc.md`

#### ファイル形式（タイムライン）
`# Timeline` セクションの下に、以下の形式でエントリを追記します。

```md
# Timeline

- HH:MM [phase] act: <やったこと>
  evd: <根拠（コマンド、ログ、リンクなど）>
  block: <詰まり（無ければ 'なし'）>
```

※ `phase` は `planning`, `coding`, `review`, `fix`, `closing` のいずれかを推奨します。

### 設定ファイルの準備

`kuroko.config.yaml` を作成し、監視対象のプロジェクトを登録します。
設定ファイルは実行ディレクトリ、または `~/.config/kuroko/config.yaml` から読み込まれます。

```yaml
version: 1
projects:
  - name: my-project
    root: /path/to/my-project
defaults:
  max_depth: 2  # 探索する深さ（デフォルトは無制限）
```

### コマンド

```bash
# 直近の活動を表示
kuroko recent

# ブロッカーを表示
kuroko blockers

# 各プロジェクトの最新ステータスを表示
kuroko status

# 人間が読みやすいMarkdownレポートを生成
kuroko report output.md

# レポート生成のオプション例（特定のプロジェクトやIssueで絞り込み）
kuroko report output.md --project my-project --issue 123 --since 2026-02-01

# LLM用にJSON形式で出力
kuroko status --json-output
```

## LLMエージェントへの統合（推奨）

LLMエージェント（Gemini CLIなど）を使用している場合、`checkpoint` スキルを導入することで、エージェントが自動的に適切な形式で証跡を残せるようになります。
具体的なスキルの定義例は [example/checkpoint_skill.md](example/checkpoint_skill.md) を参照してください。

## 免責事項 (Disclaimer)

このプロジェクトは個人利用を目的として作成されており、**無保証・無サポート**です。
本ソフトウェアの使用によって生じた、いかなる損害についても作者は一切の責任を負いません。
すべて**自己責任**でご利用ください。

## ライセンス

[MIT License](LICENSE)
