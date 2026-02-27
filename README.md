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
uv sync
```

## 使い方

### 設定ファイルの準備

`kuroko.config.yaml` を作成し、監視対象のプロジェクトを登録します。
設定ファイルは実行ディレクトリ、または `~/.config/kuroko/config.yaml` から読み込まれます。

```yaml
version: 1
projects:
  - name: my-project
    root: /path/to/my-project
```

### コマンド

```bash
# 直近の活動を表示
uv run kuroko recent

# ブロッカーを表示
uv run kuroko blockers

# 各プロジェクトの最新ステータスを表示
uv run kuroko status

# LLM用にJSON形式で出力
uv run kuroko status --json-output
```

## 免責事項 (Disclaimer)

このプロジェクトは個人利用を目的として作成されており、**無保証・無サポート**です。
本ソフトウェアの使用によって生じた、いかなる損害についても作者は一切の責任を負いません。
すべて**自己責任**でご利用ください。

## ライセンス

[MIT License](LICENSE)
