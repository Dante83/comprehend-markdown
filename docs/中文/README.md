# comprehend-markdown

*你触碰卷轴，低诵咒语。数分钟至一小时后（取决于卷轴的厚重程度），你将能洞悉任何语言编写的 Markdown。*

这是一个 MCP 服务器，可将项目的 `README.md` 翻译成其他语言；同时提供一个独立流水线，利用本地 LM Studio 模型运行“撰写-评审”循环。

源语言和目标语言均可配置——英文仅为默认选项。你可以将 `source_language` 设置为中文、印尼语或任何其他语言作为*翻译起点*，并设置 `target_languages` 来选择将其*分发至*哪些语言（详见 [选择源语言和目标语言](#选择源语言和目标语言)）。

对于任何目标项目，它期望（并在需要时创建）以下结构：

```
<project-root>/docs/<source>/README.md  标准源文件（默认英文）
<project-root>/docs/<lang>/README.md    翻译版本，每种语言一个
<project-root>/README.md                语言选择落地页（自动生成）
```

尚未迁移的项目（源文件仍在根目录）同样适用：根目录的 `README.md` 将被用作源文件，并在 `pipeline` 运行结束时被移动到 `docs/<source>/`（例如 `docs/English/`），随后由一个简短的生成落地页取代，该页面链接到所有可用的翻译版本。

## Setup (安装)

所有步骤（虚拟环境创建、依赖安装/同步）均由 `run.sh` 处理——无需单独的安装步骤。它从 `requirements.txt` 读取包并在每次运行时重新安装，因此更新依赖只需再次运行即可。

如果你想指向默认值以外的本地 LM Studio 模型，请复制示例配置并进行编辑：

```bash
cp config.local.json.example config.local.json
```

`config.local.json` 已被 gitignore 忽略，并且会逐项覆盖 `config.json` 的键值，因此你可以在不触动提交的默认设置的情况下，在本地调整 `lm_studio_url` / `model_name` / `api_key`。

### 选择源语言和目标语言

两个配置键控制翻译方向，服务器和流水线均读取这些配置（来自 `config.py`），因此两者始终保持一致：

- **`source_language`** — 你的标准 `README.md` 所使用的语言，也是其 `docs/<source_language>/` 文件夹的名称。默认为 `"English"`。将其设置为 `"中文"`、`"Bahasa Indonesia"` 或其他任何语言，即可将该语言作为*翻译起点*。
- **`target_languages`** — 流水线*翻译至*的语言列表。任何与 `source_language` 相同的条目都会被自动跳过，因此在列表中保留源语言是无害的。

例如，要将中文 README 翻译成英文和西班牙文：

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

如果省略 `target_languages`，流水线将回退到内置的 18 种语言列表。

只有在 LM Studio 的 Developer 服务器设置中开启了 "Require API Key" 时，`api_key` 才会生效——否则请将其保持为 `"lm-studio"`（LM Studio 会忽略此值）。请注意，这仅适用于 `pipeline` 模式，因为它是唯一直接调用 LM Studio OpenAI 兼容端点的部分；`serve` 模式永远不会直接与 LM Studio 的 API 通信，因为此时 LM Studio *本身* 就是调用该服务器的 MCP 客户端。

## Usage (使用)

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCP 服务器
./run.sh pipeline /absolute/path/to/project   # 端到端运行 main.py
```

两种模式均需要包含待翻译 `README.md` 的项目文件夹的**绝对**路径。在 `pipeline` 模式下，如果你是在终端交互式运行，可以省略路径并在提示时输入：

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

（`serve` 模式不会弹出提示——一旦启动，stdin/stdout 即成为 MCP JSON-RPC 通道，且 MCP 主机通常是以非交互方式启动它的。）

### `serve` — 作为 MCP 主机工具

这是 MCP 主机（如 LM Studio）在服务器 `command` 中应指向的内容，并将目标项目的绝对路径作为固定参数。它提供以下接口：

- **tool** `write_readme(language, content)` — 写入 `docs/<language>/README.md` (写入指定语言 README)
- **tool** `write_directory_readme(content)` — 写入根目录 `README.md` (写入语言选择落地页)
- **resource** `docs://readme` — 源文件 (`docs/<source_language>/README.md`，若不存在则回退至根目录 `README.md`)
- **resource** `docs://readme/{language}` — 已有的翻译版本（如果有）
- **resource** `docs://dir_readme` — 根目录 `README.md` (语言选择页)
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — 新翻译循环 (翻译 $\rightarrow$ 评审 $\rightarrow$ 重写)
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — 更新路径：将现有翻译与当前源文件对比，并以最小改动进行修补
- **prompt** `create_docs_language_directory` — 根据可用翻译列表构建根目录语言选择页

由主机自身的模型驱动工具调用；本服务器仅提供文件 I/O 和提示词模板。

#### 添加到 LM Studio

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

第二个 `args` 条目在连接时是固定的——LM Studio 的配置是静态 JSON，不支持交互式提示，因此必须填写你想要翻译的实际路径，除非你想翻译的是本仓库本身。

### `pipeline` — 独立运行，无需 MCP 主机

针对配置的 `target_languages`（默认列表包含 18 种：Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá —— 详见 [选择源语言和目标语言](#选择源语言和目标语言) 以修改列表或源语言）自行运行完整的“翻译 $\rightarrow$ 评审 $\rightarrow$ 修订”循环。它直接调用 LM Studio 的 OpenAI 兼容端点进行撰写/评审，并通过 stdio 启动内部的 `server.py` 副本来处理文件 I/O。这对于无需通过 LM Studio UI 操作的批量翻译非常有用。在本地模型上，运行时间随文档大小而变化——小型 README 需数分钟，大型分块文档可能需要一小时左右。

已经存在 `docs/<language>/README.md` 的语言不会从头开始重新翻译：评审员会将现有翻译与当前源文件进行对比，仅在内容发生变化时，撰写员才会进行最小幅度的修补。已更新的翻译将被完全跳过，因此在编辑 README 后重新运行流水线仅会处理过时部分。

在完成每种语言的工作后，运行结束时（如果需要）会将根目录的源 `README.md` 移动到 `docs/<source_language>/` 中，并重新生成根目录 `README.md` 为一个链接所有非空翻译版本的简短语言选择页。

要求 LM Studio 的本地服务器正在运行（见 `config.json`）且已加载任何聊天模型——流水线通过纯文本补全驱动模型并自行执行文件写入，因此模型**不需要**支持 OpenAI 风格的工具调用（详见下文“大型 README 处理”）。在信任全量运行之前，建议先测试一种语言。

### 大型 README 处理

使用本地模型在单次补全中翻译大型 README（例如 `A-Starry-Sky` / `a-restless-ocean` 的文档约为 35–60 KB）是主要的可靠性风险：模型可能会在运行中途耗尽输出 token 或上下文，导致尾部被静默截断。`pipeline` 模式的设计旨在避免此问题：

- **设计上无需工具调用 (Tool-free by design)。** 模型仅生成纯文本——每次翻译、重写和目录页都作为其回复返回，由编排器通过服务器的 `write_readme` / `write_directory_readme` 工具自行保存。没有任何步骤要求模型将整个文档塞进工具调用的参数中。在本地*推理*模型（如 Gemma 4）上，这种路径会截断参数 JSON 并导致端点报 `peg-gemma4 format` / 输出格式错误；返回纯文本则完全避开了这个问题。
- **`max_tokens`** (默认 `32768`) 在每次补全时被显式发送，以确保完整的章节/草稿能够完成，而不会在 LM Studio 较小的单次请求默认值处被切断。如果补全仍因 `length`（长度）停止，流水线会发出警告，提示你提高该值。
- **章节分块 (Section chunking)** — 当源文件超过 `chunk_threshold_chars` (默认 `12000`) 且 `chunk_translation` 为 `true` 时，源文件将根据顶级 (`## `) Markdown 标题进行拆分（具备代码块感知能力，因此代码块内部的 `##` 会被忽略）。每个章节在独立的补全中进行翻译，最后由编排器组装并保存。没有任何一次模型调用需要输出整个文档。
- **逐节评审 (Per-section review)** — 当 `review_sections` 为 `true`（默认值）时，每个章节都会运行与单次路径相同的“评审 $\rightarrow$ 修订”循环，但范围仅限于该章节：评审员将翻译后的章节与源内容对比，撰写员不断修订直到评审员认可（或达到 `MAX_ITERATIONS`）。由于单个章节较小，评审和重写过程远低于导致大型 README 全文评审不安全的截断阈值。

分块路径在之后**故意不运行**第二次全文评审——因为在单次补全中重新输出整个大型 README 会再次引入截断风险，且逐节评审已经覆盖了所有内容。将 `review_sections` 设置为 `false` 可在无评审的情况下翻译大型文档，或将 `chunk_translation` 设置为 `false` 以强制执行原始的单次处理行为（该行为仍会运行完整的全文评审循环）。低于阈值的单次路径保持不变。