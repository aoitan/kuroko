# Architecture & Database Design: Memo Collection & Chunking (Phase 2)

## 1. 概要
`kuroko` におけるメモ収集および構造化（チャンク化）の設計ドキュメントです。プロジェクト内の `memo.md` を収集し、検索やLLM解析に適した単位（チャンク）に分割して永続化するためのデータ構造と、設計上の重要な決定事項を記録します。

## 2. システム構成
3層アーキテクチャに基づき、関心を分離しています。

1.  **UI Layer (`kuroko/cli.py`)**: ユーザー入力を受け取り、設定をロードし、コレクターを実行する。
2.  **Logic Layer (`kuroko/memo_collector.py`, `kuroko/chunker.py`)**: 
    - ファイルシステムを走査し、ハッシュ計算とDBへの登録・更新判断を行う。
    - 収集したテキストを空行や見出しに基づき「チャンク」に分割する。
3.  **Core Layer (`kuroko_core/db.py`)**: SQLite接続の管理（外部キー制約の有効化）、スキーマ定義、原子的なデータ操作を担う。

## 3. データベース設計 (SQLite)

### テーブル: `source_texts`
プロジェクトから収集された原文（Raw Text）を格納する中心的なテーブルです。

| カラム名 | 型 | 制約 | 説明 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY | 内部管理用ID |
| `source_type` | TEXT | NOT NULL | ソースの種類（現在は "memo" 固定） |
| `path` | TEXT | NOT NULL UNIQUE | ファイルの絶対パス。1つのパスにつき1レコード。 |
| `directory_context` | TEXT | - | ファイルの親ディレクトリ名など、階層情報を保持。 |
| `raw_text` | TEXT | NOT NULL | ファイルから読み取った生のテキスト内容。 |
| `file_hash` | TEXT | NOT NULL | 内容の SHA-256 ハッシュ値。重複インポート防止に使用。 |
| `updated_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | **内容が変更された**最終時刻。 |
| `imported_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | **最初にインポートされた**時刻。更新時も維持。 |

### テーブル: `chunks`
原文を検索や解釈しやすい単位に分割した断片を格納します。

| カラム名 | 型 | 制約 | 説明 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY | 内部管理用ID |
| `source_id` | INTEGER | NOT NULL | `source_texts(id)` への外部キー |
| `chunk_index` | INTEGER | NOT NULL | 同一原文内での順序（0開始） |
| `chunk_text` | TEXT | NOT NULL | 分割されたテキスト内容 |
| `heading` | TEXT | - | 該当チャンクが属する直前の見出し内容 |
| `block_timestamp`| TEXT | - | テキスト内から抽出された日時（YYYY-MM-DDなど） |
| `chunk_hash` | TEXT | NOT NULL | チャンク内容のハッシュ値 |

### インデックス
- `idx_source_texts_hash`: `source_texts(file_hash)` による高速な重複チェック用。
- `idx_chunks_source`: `chunks(source_id)` による特定ソースに紐づくチャンクの高速取得用。
- `idx_chunks_hash`: `chunks(chunk_hash)` によるチャンク単位の重複・変更検知用。

## 4. 設計判断 (Design Decisions)

### 4.1. チャンク分割の戦略
本実装では、LLMのコンテキストウィンドウを有効活用し、かつ意味的なまとまりを維持するために以下のルールで分割を行っています。

1.  **空行区切り**: 連続する空行をパラグラフの境界として扱い、物理的なまとまりを保持する。
2.  **見出しによる強制分割**: Markdown の見出し (`#`, `##` 等) が現れた場合、そこを新しいチャンクの開始点とする。
3.  **コンテキストの継承**: 各チャンクには、分割前のテキストで最後に出現した見出しを `heading` メタデータとして付与する。これにより、断片化されたテキストでも「何についての記述か」を保持できる。

### 4.2. 外部キー制約と整合性維持
- **SQLite 外部キー**: 接続ごとに `PRAGMA foreign_keys = ON;` を実行し、`source_texts` と `chunks` の間の親子関係を強制する。
- **カスケード削除**: `ON DELETE CASCADE` を定義。原文（`source_texts`）が削除または更新される際、古いチャンクが自動的に削除され、孤立データ（ゴミ）が残るのを防ぐ。

### 4.3. パスベース vs ハッシュベースの重複排除（再定義）
Phase 2 では、以下の優先順位で処理を行います。

1.  **パス優先 (Path-First)**: 
    - まずファイルの「パス」を確認する。
    - すでにDBに存在するパスで、かつハッシュが一致していれば完全にスキップする。
    - ハッシュが異なる場合は、既存レコードと全チャンクを更新する。
2.  **グローバル重複排除 (Global Deduplication)**:
    - パスが新規の場合のみ、内容（ハッシュ）が他プロジェクトを含め既に存在するか確認し、存在すればインポートをスキップする。
    - **判断理由**: 同一内容のメモが複数箇所にある場合の冗長性を排除しつつ、既存ファイルの「内容変更」を確実に追跡するため。

## 5. 将来の拡張性への考慮
- **ベクトル検索 (RAG)**: `chunks` テーブルに `embedding` カラム（ベクトルデータ）を追加することで、そのままRAG（検索補完生成）の基盤として利用可能。
- **メタデータの充実**: チャンクごとにLLMで生成した「要約」や「キーワード」を保存するカラムを追加することで、検索精度をさらに向上させることが可能。
