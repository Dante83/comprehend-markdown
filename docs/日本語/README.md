# comprehend-markdown

*古の巻物に触れ、呪文を唱える。数分から一時間後（巻物の厚みによる）、あらゆる言語のMarkdownがあなたの理解へと変わる。*

プロジェクトの `README.md` を他言語に翻訳するMCPサーバーです。また、ローカルのLM Studioモデルを使用してライター/レビュアー・ループを実行するスタンドアロンのパイプライン機能も備えています。

ソース言語とターゲット言語はどちらも設定可能です（デフォルトは英語）。`source_language` を設定することで中国語やインドネシア語などから翻訳を開始でき、`target_languages` で展開先の言語を選択できます（詳細は [ソース言語とターゲット言語の選択](#ソース言語とターゲット言語の選択) を参照してください）。

ターゲットとなるプロジェクトでは、以下の構成を想定しています（必要に応じて自動的に作成されます）。

```
<project-root>/docs/<source>/README.md  正本（デフォルトは英語）
<project-root>/docs/<lang>/README.md    翻訳済みバージョン（言語ごとに1つ）
<project-root>/README.md                言語選択用のランディングページ（自動生成）
```

まだ移行されていないプロジェクト（ソースがルートにある状態）でも動作します。その場合、ルートの `README.md` がソースとして使用され、`pipeline` の実行完了時に `docs/<source>/`（例：`docs/English/`）へ移動されます。その後、利用可能なすべての翻訳へのリンクを含む短いランディングページがルートに生成されます。

## セットアップ

仮想環境の作成や依存関係のインストール・同期はすべて `run.sh` で処理されるため、個別のインストール手順は不要です。`requirements.txt` からパッケージを読み込み、実行ごとに再インストールを行うため、新しい依存関係を取り込むには再度スクリプトを実行するだけで済みます。

デフォルト以外のローカルLM Studioモデルを使用したい場合は、`config.json` の値を変更してください。

### ソース言語とターゲット言語の選択

`config.json` の2つの設定キーで翻訳方向を制御します。

- **`source_language`** — 正本となる `README.md` が書かれている言語であり、`docs/<source_language>/` フォルダの名前になります。デフォルトは `English` です。中国語 (`中文`) やインドネシア語 (`Indonesia`) などから翻訳したい場合は、ここを変更してください。
- **`target_languages`** — パイプラインが翻訳を行う先の言語リストです。`source_language` と同じ言語が含まれている場合は自動的にスキップされるため、リストにソース言語を残していても問題ありません。

例：中国語のREADMEを英語とスペイン語に翻訳する場合：

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

`target_languages` を省略した場合、パイプラインは内蔵の18言語リストを使用します。

`api_key` は、LM StudioのDeveloperサーバー設定で「Require API Key」を有効にしている場合にのみ必要です。それ以外の場合は `"lm-studio"` のままで構いません（LM Studio側で無視されます）。なお、これは LM Studio の OpenAI 互換エンドポイントを直接呼び出す `pipeline` モードにのみ適用されます。`serve` モードでは、LM Studio 自体が MCP クライアントとしてサーバーを呼び出すため、LM Studio の API と通信することはありません。

`max_tokens` も設定可能ですが、LM Studio がこれを厳密に遵守するかは不明です。このスクリプトを実行する前に、モデル自体の設定で `max_tokens` を少なくとも 24576 程度に設定してください。

## 使い方

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCPサーバーとして起動
./run.sh pipeline /absolute/path/to/project   # main.py をエンドツーエンドで実行
```

どちらのモードでも、翻訳対象の `README.md` が含まれるプロジェクトフォルダへの **絶対パス** が必要です。ターミナルで対話的に実行している場合、`pipeline` モードではパスを省略して後から入力することも可能です。

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

（`serve` モードではプロンプトは表示されません。起動後は stdin/stdout が MCP JSON-RPC チャネルとして使用されるためです。また、MCPホストは通常、非対話的にこれを起動します。）

### `serve` — MCPホストツールとして利用する

MCPホスト（例：LM Studio）のサーバー設定の `command` に指定して使用します。この際、ターゲットプロジェクトの絶対パスを固定引数として渡してください。以下の機能を提供します。

- **tool** `write_readme(language, content)` — `docs/<language>/README.md` を書き込む
- **tool** `write_directory_readme(content)` — ルートの `README.md`（言語選択ページ）を書き込む
- **resource** `docs://readme` — ソースファイル (`docs/<source_language>/README.md`、なければルートの `README.md`)
- **resource** `docs://readme/{language}` — 既存の翻訳ファイル（存在する場合）
- **resource** `docs://dir_readme` — ルートの `README.md`
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — 新規翻訳ループ用プロンプト
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — 更新パス用：既存の翻訳を現在のソースと比較し、最小限の変更で修正する
- **prompt** `create_docs_language_directory` — 利用可能な翻訳リストからルートの言語選択ページを作成する

ツール呼び出しはホスト側のモデルが制御し、このサーバーはファイル I/O とプロンプトテンプレートのみを提供します。

#### LM Studio への追加方法

LM Studio の MCP 設定ファイルは `~/.lmstudio/mcp.json` にあります。以下のようにエントリを追加してください。

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/absolute/path/to/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/absolute/path/to/the/project/you/want/to/translate"
      ]
    }
  }
}
```

2番目の `args` エントリは接続時に固定されます。LM Studio の設定は静的な JSON であり、対話的なプロンプトをサポートしていないため、翻訳したいプロジェクトの実際のパスを指定する必要があります（このリポジトリ自体を翻訳したい場合を除き、リポジトリ自身のパスを指定しないでください）。