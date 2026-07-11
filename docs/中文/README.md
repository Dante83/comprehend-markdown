# comprehend-markdown

*你触碰卷轴，低诵咒语。数分钟至一小时后（取决于卷轴的厚重程度），你将洞悉任何语言的 Markdown。*

这是一个 MCP 服务器，可将项目的 `README.md` 翻译成其他语言；同时它还提供一个独立流水线，利用本地 LM Studio 模型运行“撰写/评审”循环。

源语言和目标语言均可配置——英文仅为默认选项。你可以将 `source_language` 设置为中文、印尼语或任何其他语言以将其作为翻译起点，并设置 `target_languages` 来选择分发的目标语言（详见 [选择源语言和目标语言](#choosing-source-and-target-languages)）。

对于任何目标项目，它期望（并在需要时创建）以下结构：

```
<project-root>/docs/<source>/README.md  标准源文件（默认英文）
<project-root>/docs/<lang>/README.md    翻译版本，每种语言一个
<project-root>/README.md                语言选择落地页（自动生成）
```

尚未迁移的项目（源文件仍在根目录）同样适用：根目录的 `README.md` 将被用作源文件，在 `pipeline` 运行结束时，它会被移动到 `docs/<source>/`（例如 `docs/English/`），并由一个生成的简短落地页取代，该页面会链接到所有可用的翻译版本。

## Setup (安装与设置)

所有操作（创建 venv、安装/同步依赖）均由 `run.sh` 处理——无需单独的安装步骤。它从 `requirements.txt` 读取包并在每次运行时重新安装，因此获取新依赖只需再次运行即可。

如果你想指向默认值以外的本地 LM Studio 模型，请修改 `config.json` 中的值。

### Choosing source and target languages (选择源语言和目标语言)

`config.json` 中的两个配置键控制翻译方向：

- **`source_language`** — 你的标准 `README.md` 所使用的语言，也是其 `docs/<source_language>/` 文件夹的名称。默认为 `English`。将其设置为 `中文`、`Indonesia` 或任何其他语言，即可将该语言作为翻译源。
- **`target_languages`** — 流水线翻译的目标语言列表。任何与 `source_language` 相同的条目都会被自动跳过，因此将源语言留在列表中没有影响。

例如，要将中文 README 翻译成英文和西班牙文：

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

如果省略 `target_languages`，流水线将回退到内置的 18 种语言列表。

只有当你开启了 LM Studio 开发者服务器设置中的 "Require API Key" 时，`api_key` 才会生效——否则请将其保持为 `"lm-studio"`（LM Studio 会忽略此值）。请注意，这仅适用于 `pipeline` 模式，因为它是唯一直接调用 LM Studio OpenAI 兼容端点的部分；`serve` 模式永远不会直接与 LM Studio 的 API 通信，因为此时 LM Studio *本身* 就是调用该服务器的 MCP 客户端。

这里可以设置 `max_tokens`，但我不确定 LM Studio 是否真的遵循此设置。请确保在运行此脚本之前，在模型本身的设置中将此值设置为至少 24576。

## Usage (使用方法)

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCP 服务器
./run.sh pipeline /absolute/path/to/project   # 端到端运行 main.py
```

两种模式都要求提供包含待翻译 `README.md` 的项目文件夹的**绝对**路径。在 `pipeline` 模式下，如果你是在终端交互式运行，可以省略路径，程序会提示你输入：

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

（`serve` 模式不会弹出提示——一旦启动，stdin/stdout 即成为 MCP JSON-RPC 通道，且 MCP 主机通常是以非交互方式启动它的。）

### `serve` — 作为 MCP 主机工具

这是 MCP 主机（如 LM Studio）在服务器 `command` 中应指向的内容，并将目标项目的绝对路径作为固定参数。它提供以下接口：

- **tool** `write_readme(language, content)` (写入 README) — 写入 `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` (写入目录 README) — 写入根目录 `README.md`（语言选择落地页）
- **resource** `docs://readme` (读取源文件) — 读取源文件 (`docs/<source_language>/README.md`，若不存在则回退至根目录 `README.md`)
- **resource** `docs://readme/{language}` (读取翻译件) — 读取已有的翻译版本（如果有）
- **resource** `docs://dir_readme` (读取落地页) — 读取根目录 `README.md`
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` (翻译循环) — 完整的“翻译-评审-重写”循环提示词
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` (更新路径) — 更新流程：将现有翻译与当前源文件对比，并以最小改动进行修补
- **prompt** `create_docs_language_directory` (创建语言目录) — 根据可用翻译列表构建根目录语言选择页面

由主机自身的模型驱动工具调用；本服务器仅提供文件 I/O 和提示词模板。

#### Adding it to LM Studio (添加到 LM Studio)

LM Studio 的 MCP 配置位于 `~/.lmstudio/mcp.json`。添加如下条目：

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

第二个 `args` 条目在连接时是固定的——LM Studio 的配置是静态 JSON，不支持交互式提示，因此这里必须填写你想要翻译的项目实际路径，除非你想翻译的是本仓库本身。