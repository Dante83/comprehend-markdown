# comprehend-markdown

*古の巻物に触れ、呪文を唱える。数分から一時間後（巻物の厚みによる）、あらゆる言語のMarkdownが理解できるようになる。*

プロジェクトの `README.md` を他言語に翻訳するMCPサーバーであり、同時にローカルのLM Studioモデルを使用して「執筆者/校閲者ループ」を実行するスタンドアロン・パイプラインです。

ソース言語とターゲット言語はどちらも設定可能です（デフォルトは英語）。`source_language` を設定することで中国語やインドネシア語などから翻訳を開始でき、`target_languages` で展開先の言語を選択できます（詳細は [ソース言語とターゲット言語の選択](#ソース言語とターゲット言語の選択) を参照してください）。

ターゲットとなるプロジェクトでは、以下の構成を想定しています（必要に応じて自動的に作成されます）：

```
<project-root>/docs/<source>/README.md  正本（デフォルトは英語）
<project-root>/docs/<lang>/README.md    翻訳版（言語ごとに1つ）
<project-root>/README.md                言語選択用のランディングページ（自動生成）
```

まだ移行されていないプロジェクト（ソースがルートにある場合）でも動作します。その場合、ルートの `README.md` がソースとして使用され、`pipeline` の実行終了時に `docs/<source>/`（例：`docs/English/`）に移動されます。その後、利用可能なすべての翻訳へのリンクを含む短いランディングページがルートの `README.md` として生成されます。

## セットアップ

仮想環境（venv）の作成や依存関係のインストール・同期はすべて `run.sh` で処理されるため、個別のインストール手順は不要です。`requirements.txt` からパッケージを読み込み、実行のたびに再インストールするため、新しい依存関係を取り込むには再度実行するだけで済みます。

デフォルト以外のローカルLM Studioモデルを指定したい場合は、設定例をコピーして編集してください：

```bash
cp config.local.json.example config.local.json
```

`config.local.json` は `.gitignore` に指定されており、`config.json` の設定をキー単位で上書きします。これにより、コミット済みのデフォルト値を変更することなく、ローカルで `lm_studio_url` / `model_name` / `api_key` を調整できます。

### ソース言語とターゲット言語の選択

翻訳方向は2つの設定キーで制御されます。サーバーとパイプラインの両方がこれら（`config.py` から）を読み込むため、不整合が起こることはありません：

- **`source_language`** — 正本となる `README.md` が書かれている言語であり、`docs/<source_language>/` フォルダの名前になります。デフォルトは `"English"` です。中国語 (`"中文"`) やインドネシア語 (`"Bahasa Indonesia"`) などから翻訳したい場合は、ここを変更してください。
- **`target_languages`** — パイプラインが翻訳を行う先の言語リストです。`source_language` と同じエントリは自動的にスキップされるため、リストにソース言語が含まれていても問題ありません。

例：中国語のREADMEを英語とスペイン語に翻訳する場合：

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

`target_languages` を省略した場合、パイプラインは内蔵の18言語リストを使用します。

`api_key` は、LM StudioのDeveloperサーバー設定で「Require API Key」を有効にしている場合にのみ必要です。それ以外の場合は `"lm-studio"` のままで構いません（LM Studio側で無視されます）。なお、これは `pipeline` モードにのみ適用されます。`pipeline` はLM StudioのOpenAI互換エンドポイントを直接呼び出すためです。一方、`serve` モードはMCPクライアントであるLM Studioから呼び出される側であるため、LM StudioのAPIと直接通信することはありません。

## 使い方

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCPサーバーとして起動
./run.sh pipeline /absolute/path/to/project   # main.py をエンドツーエンドで実行
```

どちらのモードでも、翻訳対象の `README.md` が含まれるプロジェクトフォルダへの **絶対パス** が必要です。`pipeline` モードをターミナルで対話的に実行する場合は、パスを省略してプロンプトに従うことも可能です：

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

（`serve` モードではプロンプトは表示されません。起動後、標準入力/出力はMCP JSON-RPCチャネルとして使用され、MCPホストは非対話的にこれを起動するためです。）

### `serve` — MCPホストツールとして

これは、MCPホスト（例：LM Studio）がサーバーの `command` に指定すべきモードです。ターゲットプロジェクトの絶対パスを固定引数として渡します。以下の機能を提供します：

- **tool** `write_readme(language, content)` — `docs/<language>/README.md` を書き込みます
- **tool** `write_directory_readme(content)` — ルートの `README.md`（言語選択ページ）を書き込みます
- **resource** `docs://readme` — ソースファイル (`docs/<source_language>/README.md`、なければルートの `README.md`)
- **resource** `docs://readme/{language}` — 既存の翻訳がある場合はそれを返します
- **resource** `docs://dir_readme` — ルートの `README.md`
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — 新規翻訳ループ用
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — 更新パス：既存の翻訳を現在のソースと比較し、最小限の変更でパッチを適用します
- **prompt** `create_docs_language_directory` — 利用可能な翻訳リストからルートの言語選択ページを作成します

ツール呼び出しはホスト側のモデルが制御し、このサーバーはファイルI/Oとプロンプトテンプレートのみを提供します。

#### LM Studioへの追加方法

LM StudioのMCP設定ファイルは `~/.lmstudio/mcp.json` にあります。以下のようなエントリを追加してください：

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

2番目の `args` エントリは接続時に固定されます。LM Studioの設定は静的なJSONであり対話的なプロンプトをサポートしていないため、翻訳したいプロジェクトの実際のパスを指定する必要があります（このリポジトリ自体を翻訳したい場合を除き、リポジトリ自身のパスを指定しないでください）。

### `pipeline` — スタンドアロンモード（MCPホスト不要）

設定された `target_languages` に対して、「翻訳 $\rightarrow$ 批評 $\rightarrow$ 修正」のフルループを単独で実行します（デフォルトの18言語：ドイツ語、スペイン語、フランス語、イタリア語、ポーランド語、ポルトガル語、ロシア語、ベトナム語、タイ語、中国語、日本語、韓国語、アラビア語、ヒンディー語、ベンガル語、インドネシア語、ウルドゥー語、ナイジャ語。リストやソース言語を変更するには [ソース言語とターゲット言語の選択](#ソース言語とターゲット言語の選択) を参照してください）。

執筆者/校閲者のターンごとにLM StudioのOpenAI互換エンドポイントを直接呼び出し、ファイルI/Oを行うために内部的に `server.py` のコピーをstdio経由で起動します。LM StudioのUIを介さずにバッチ翻訳を行いたい場合に便利です。実行時間はローカルモデルでのドキュメントサイズに依存し、小さなREADMEなら数分、巨大なファイルを分割して処理する場合は1時間ほどかかることがあります。

すでに `docs/<language>/README.md` が存在する言語については、ゼロから再翻訳しません。校閲者が既存の翻訳を現在のソースと比較し、変更があった場合にのみ執筆者が最小限の編集でパッチを適用します。最新の状態である翻訳は完全にスキップされるため、READMEを編集した後にパイプラインを再実行しても、古くなった部分だけが更新されます。

各言語の処理が終わると、（必要に応じて）ルートレベルのソース `README.md` を `docs/<source_language>/` に移動し、空でないすべての翻訳へのリンクを含む短い言語選択ページとしてルートの `README.md` を再生成して終了します。

このモードには、チャットモデルがロードされた状態でLM Studioのローカルサーバーが動作している必要があります（`config.json` を参照）。パイプラインはプレーンテキストの補完でモデルを駆動し、ファイル書き込み自体はプログラム側で行うため、モデルがOpenAIスタイルのツール呼び出し (tool calls) をサポートしている必要はありません（詳細は後述の「巨大なREADMEの処理」を参照）。まずは1つの言語でテストしてから、全リストでの実行を試すことをお勧めします。

### 巨大なREADMEの処理

巨大なREADME（例：姉妹プロジェクトである `A-Starry-Sky` や `a-restless-ocean` のドキュメントは約35〜60 KBあります）を一度の補完で翻訳しようとすると、ローカルモデルでは信頼性のリスクが高まります。出力トークンやコンテキストが途中で不足し、末尾が静かに切り捨てられることがあるためです。`pipeline` モードはこれを回避するように設計されています：

- **意図的なツールレス設計**: モデルは常にプレーンテキストのみを生成します。すべての翻訳、書き直し、ディレクトリページはモデルの返答として返され、オーケストレーターがサーバーの `write_readme` / `write_directory_readme` ツールを通じて保存します。ドキュメント全体をツール呼び出しの引数に詰め込むことはありません。Gemma 4のようなローカルの推論モデルでは、引数のJSONが切り捨てられてエンドポイントが `peg-gemma4 format` / malformed-output エラーを返すことがありますが、テキストで返させることでこれを完全に回避しています。
- **`max_tokens`**: すべての補完において明示的に `max_tokens`（デフォルト `32768`）を送信します。これにより、LM Studioの小さなリクエストデフォルト値で途切れることなく、セクションやドラフト全体を完了させることができます。それでも `length` で停止した場合は警告が表示されるため、値を上げる必要があることがわかります。
- **セクション・チャンキング**: ソースが `chunk_threshold_chars`（デフォルト `12000`）を超え、かつ `chunk_translation` が `true` の場合、ソースはトップレベルのMarkdown見出し (`## `) で分割されます（コードブロック内の `##` は無視されます）。各セクションは個別の補完で翻訳され、オーケストレーターがそれらを組み立てて保存します。一度のモデル呼び出しでドキュメント全体を出力させる必要はありません。
- **セクションごとのレビュー**: `review_sections` が `true`（デフォルト）の場合、各セクションに対して単発パスと同じ「批評 $\rightarrow$ 修正」ループが実行されます。校閲者が翻訳されたセクションをソースと比較し、執筆者が修正を行い、校閲者が合意するか `MAX_ITERATIONS` に達するまで繰り返します。セクション単位であればサイズが小さいため、巨大なREADME全体のレビューで発生していた切り捨てのリスクを回避できます。

チャンク処理パスでは、その後の「ドキュメント全体の二次レビュー」はあえて行いません。巨大なREADME全体を一度に再出力させると再び切り捨てが発生するためです。セクションごとのパスで十分な品質が確保されています。レビューなしで巨大なドキュメントを翻訳したい場合は `review_sections` を `false` に、元の単発動作（ドキュメント全体のレビューループを含む）を強制したい場合は `chunk_translation` を `false` に設定してください。しきい値以下のサイズのドキュメントに対する挙動は変わりません。