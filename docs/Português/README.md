# comprehend-markdown

*Você toca o pergaminho e pronuncia o encantamento. Minutos ou até uma hora depois (por documento, dependendo da densidade do pergaminho), você compreende o Markdown em qualquer língua.*

Um servidor MCP que traduz o `README.md` de um projeto para outros idiomas, além de um pipeline independente que executa um ciclo de escrita e revisão utilizando um modelo local do LM Studio.

Tanto o idioma de origem quanto os de destino são configuráveis — o inglês é apenas o padrão. Defina `source_language` para traduzir *a partir* de chinês, indonésio ou qualquer outro idioma, e `target_languages` para escolher para quais idiomas ele deve se ramificar (veja [Escolhendo os idiomas de origem e destino](#escolhendo-os-idiomas-de-origem-e-destino)).

Para qualquer projeto de destino, o sistema espera (e cria, se necessário):

```
<project-root>/docs/<source>/README.md  a fonte canônica (Inglês por padrão)
<project-root>/docs/<lang>/README.md    versões traduzidas, uma por idioma
<project-root>/README.md                página de entrada para seleção de idioma (gerada)
```

Projetos que ainda não foram migrados — onde a fonte ainda está na raiz — também funcionam: o `README.md` da raiz é usado como fonte e, ao final de uma execução do `pipeline`, ele é movido para `docs/<source>/` (ex: `docs/English/`) e substituído por uma página de entrada curta e gerada que linka todas as traduções disponíveis.

## Setup

Tudo (criação do venv, instalação/sincronização de dependências) é gerenciado pelo `run.sh` — não há etapa de instalação separada. Ele lê os pacotes do `requirements.txt` e os reinstala a cada execução, portanto, atualizar as dependências significa apenas executá-lo novamente.

Se você quiser apontar para um modelo local do LM Studio diferente do padrão, modifique os valores em `config.json`.

### Escolhendo os idiomas de origem e destino

Duas chaves de configuração no `config.json` controlam a direção da tradução:

- **`source_language`** — o idioma em que seu `README.md` canônico está escrito e o nome de sua pasta `docs/<source_language>/`. O padrão é `English`. Defina como `中文`, `Indonesia` ou qualquer outro para traduzir *a partir* desse idioma.
- **`target_languages`** — a lista para a qual o pipeline traduz. Qualquer entrada igual ao `source_language` é ignorada automaticamente, então manter a origem na lista não causa problemas.

Por exemplo, para traduzir um README em chinês para inglês e espanhol:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Se `target_languages` for omitido, o pipeline utilizará sua lista interna de 18 idiomas.

A `api_key` só é relevante se você ativou a opção "Require API Key" nas configurações do servidor Developer do LM Studio — caso contrário, deixe como `"lm-studio"`, que é ignorado pelo LM Studio. Note que isso se aplica apenas ao modo `pipeline`, que é a única parte que chama o endpoint compatível com OpenAI do LM Studio diretamente; o modo `serve` nunca fala com a API do LM Studio, pois o próprio LM Studio *é* o cliente MCP que faz as chamadas para ele.

O campo `max_tokens` está disponível para configuração, mas não tenho certeza se o LM Studio realmente o respeita. Certifique-se de definir este valor para pelo menos 24576 no próprio modelo antes de executar este script.

## Uso

```bash
./run.sh serve    /caminho/absoluto/para/o/projeto   # servidor MCP stdio
./run.sh pipeline /caminho/absoluto/para/o/projeto   # executa o main.py de ponta a ponta
```

Ambos os modos exigem um caminho **absoluto** para a pasta do projeto que contém o `README.md` a ser traduzido. No modo `pipeline`, você pode omiti-lo e será solicitado a informá-lo, desde que esteja executando interativamente em um terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /caminho/absoluto/para/o/projeto
```

(O modo `serve` nunca solicita informações — assim que inicia, o stdin/stdout tornam-se o canal JSON-RPC do MCP, e os hosts MCP o iniciam de forma não interativa.)

### `serve` — como uma ferramenta de host MCP

É para este comando que um host MCP (ex: LM Studio) deve apontar seu `command` de servidor, com o caminho absoluto do projeto de destino como um argumento fixo. Ele expõe:

- **tool** `write_readme(language, content)` — escreve o arquivo `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — escreve o `README.md` da raiz (a página de seleção de idioma)
- **resource** `docs://readme` — a fonte (`docs/<source_language>/README.md`, revertendo para o `README.md` da raiz)
- **resource** `docs://readme/{language}` — a tradução existente, se houver
- **resource** `docs://dir_readme` — o `README.md` da raiz
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — o ciclo de nova tradução
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — o fluxo de atualização: compara uma tradução existente com a fonte atual e aplica correções mínimas
- **prompt** `create_docs_language_directory` — constrói a página de seleção de idioma da raiz a partir da lista de traduções disponíveis

O modelo do próprio host conduz as chamadas de ferramentas; este servidor apenas fornece a E/S de arquivos e os templates de prompt.

#### Adicionando ao LM Studio

A configuração de MCP do LM Studio fica em `~/.lmstudio/mcp.json`. Adicione uma entrada como esta:

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/caminho/absoluto/para/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/caminho/absoluto/para/o/projeto/que/voce/quer/traduzir"
      ]
    }
  }
}
```

A segunda entrada de `args` é fixada no momento da conexão — a configuração do LM Studio é um JSON estático sem suporte a prompts interativos, portanto, deve ser o caminho real que você deseja traduzir, e não o caminho deste repositório (a menos que este seja o projeto que você pretende traduzir).