# comprehend-markdown

*Você toca o pergaminho e profere a encantação. Minutos ou até uma hora depois (por documento, dependendo do peso do pergaminho), você compreende o Markdown em qualquer idioma.*

Um servidor MCP que traduz o `README.md` de um projeto para outros idiomas, além de um pipeline independente que executa um ciclo de escritor/revisor utilizando um modelo local do LM Studio.

Tanto o idioma de origem quanto os de destino são configuráveis — o inglês é apenas o padrão. Defina `source_language` para traduzir *a partir* de chinês, indonésio ou qualquer outro idioma, e `target_languages` para escolher para quais idiomas a tradução será expandida (veja [Escolhendo os idiomas de origem e destino](#escolhendo-os-idiomas-de-origem-e-destino)).

Para qualquer projeto de destino, o sistema espera (e cria, se necessário):

```
<raiz-do-projeto>/docs/<origem>/README.md  a fonte canônica (Inglês por padrão)
<raiz-do-projeto>/docs/<idioma>/README.md    versões traduzidas, uma por idioma
<raiz-do-projeto>/README.md                página inicial de seleção de idioma (gerada)
```

Projetos que ainda não foram migrados — onde a fonte ainda está na raiz — também funcionam: o `README.md` da raiz é usado como fonte e, ao final de uma execução do `pipeline`, ele é movido para `docs/<origem>/` (ex: `docs/English/`) e substituído por uma página inicial curta e gerada que linka todas as traduções disponíveis.

## Setup

Tudo (criação de venv, instalação/sincronização de dependências) é gerenciado pelo `run.sh` — não há etapa de instalação separada. Ele lê os pacotes do `requirements.txt` e os reinstala a cada execução, portanto, atualizar as dependências significa apenas executá-lo novamente.

Se você quiser apontar para um modelo local do LM Studio diferente do padrão, copie o exemplo de configuração e edite-o:

```bash
cp config.local.json.example config.local.json
```

O arquivo `config.local.json` está no `.gitignore` e sobrescreve as chaves do `config.json`, permitindo que você ajuste `lm_studio_url` / `model_name` / `api_key` localmente sem alterar os padrões commitados.

### Escolhendo os idiomas de origem e destino

Duas chaves de configuração controlam a direção da tradução, e tanto o servidor quanto o pipeline as leem (do `config.py`), garantindo que nunca haja divergência:

- **`source_language`** — o idioma em que seu `README.md` canônico está escrito e o nome de sua pasta `docs/<source_language>/`. O padrão é `"English"`. Defina como `"中文"`, `"Bahasa Indonesia"` ou qualquer outro para traduzir *a partir* desse idioma.
- **`target_languages`** — a lista para a qual o pipeline traduz. Qualquer entrada igual ao `source_language` é ignorada automaticamente, portanto, manter a origem na lista não causa problemas.

Por exemplo, para traduzir um README em chinês para inglês e espanhol:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Se `target_languages` for omitido, o pipeline utilizará sua lista interna de 18 idiomas.

A `api_key` só é relevante se você ativou a opção "Require API Key" nas configurações do servidor Developer do LM Studio — caso contrário, deixe como `"lm-studio"`, que é ignorado pelo LM Studio. Note que isso se aplica apenas ao modo `pipeline`, que é a única parte que chama o endpoint compatível com OpenAI do LM Studio diretamente; o modo `serve` nunca fala com a API do LM Studio, pois o próprio LM Studio *é* o cliente MCP que faz as chamadas para ele.

## Uso

```bash
./run.sh serve    /caminho/absoluto/para/projeto   # servidor MCP stdio
./run.sh pipeline /caminho/absoluto/para/projeto   # executa main.py de ponta a ponta
```

Ambos os modos exigem um caminho **absoluto** para a pasta do projeto que contém o `README.md` a ser traduzido. No modo `pipeline`, você pode omitir o caminho e será solicitado a digitá-lo, desde que esteja executando interativamente em um terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /caminho/absoluto/para/projeto
```

(O modo `serve` nunca solicita entrada — assim que inicia, o stdin/stdout tornam-se o canal JSON-RPC do MCP, e os hosts MCP o iniciam de forma não interativa.)

### `serve` — como uma ferramenta de host MCP

É para este comando que um host MCP (ex: LM Studio) deve apontar seu `command` de servidor, com o caminho absoluto do projeto de destino como um argumento fixo. Ele expõe:

- **tool** `write_readme(language, content)` (escreve o arquivo `docs/<language>/README.md`)
- **tool** `write_directory_readme(content)` (escreve o `README.md` da raiz — a página de seleção de idiomas)
- **resource** `docs://readme` (a fonte: `docs/<source_language>/README.md`, ou o `README.md` da raiz como fallback)
- **resource** `docs://readme/{language}` (a tradução existente, se houver)
- **resource** `docs://dir_readme` (o `README.md` da raiz)
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` (ciclo de nova tradução)
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` (fluxo de atualização: compara uma tradução existente com a fonte atual e aplica correções mínimas)
- **prompt** `create_docs_language_directory` (constrói a página de seleção de idiomas da raiz a partir da lista de traduções disponíveis)

O modelo do próprio host conduz as chamadas de ferramentas; este servidor apenas fornece a E/S de arquivos e os templates de prompts.

#### Adicionando ao LM Studio

A configuração MCP do LM Studio fica em `~/.lmstudio/mcp.json`. Adicione uma entrada como esta:

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

### `pipeline` — independente, sem host MCP

Executa sozinho todo o ciclo de tradução $\rightarrow$ crítica $\rightarrow$ revisão para os `target_languages` configurados (lista padrão de 18: Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — veja [Escolhendo os idiomas de origem e destino](#escolhendo-os-idiomas-de-origem-e-destino) para alterar a lista ou o idioma de origem), chamando diretamente o endpoint compatível com OpenAI do LM Studio para as etapas de escrita/revisão e instanciando sua própria cópia interna de `server.py` via stdio para realizar a E/S de arquivos. Útil para traduções em lote sem precisar operar pela interface do LM Studio. O tempo de execução varia conforme o tamanho do documento no modelo local — minutos para um README pequeno, até cerca de uma hora para um documento grande e fragmentado.

Idiomas que já possuem um `docs/<language>/README.md` não são traduzidos do zero: o revisor compara a tradução existente com a fonte atual e, somente se algo mudou, o escritor aplica edições mínimas. Traduções atualizadas são totalmente ignoradas, portanto, reexecutar o pipeline após editar um README processará apenas as partes obsoletas.

Após o trabalho por idioma, a execução termina (se necessário) movendo o `README.md` da raiz para `docs/<source_language>/` e regenerando o `README.md` da raiz como uma página curta de seleção de idiomas que linka todas as traduções não vazias.

Requer que o servidor local do LM Studio esteja rodando (veja `config.json`) com qualquer modelo de chat carregado — o pipeline conduz o modelo com conclusões de texto simples e realiza as escritas de arquivos por conta própria, portanto, o modelo **não** precisa suportar chamadas de ferramentas (*tool calls*) no estilo OpenAI (veja "Tratamento de READMEs extensos" abaixo). Ainda assim, recomenda-se testar um único idioma antes de confiar em uma execução completa em toda a lista.

### Tratamento de READMEs extensos

Traduzir um README grande (como as documentações irmãs `A-Starry-Sky` / `a-restless-ocean`, que têm ~35–60 KB) em uma única conclusão é o principal risco de confiabilidade em modelos locais: eles podem esgotar os tokens de saída ou o contexto no meio do caminho, truncando o final silenciosamente. O modo `pipeline` foi projetado para evitar isso:

- **Projetado para dispensar tools.** O modelo produz apenas texto simples — cada tradução, reescrita e página de diretório retorna como sua resposta, e o orquestrador a salva via as ferramentas `write_readme` / `write_directory_readme` do servidor. Nada solicita que o modelo insira um documento inteiro em um argumento de chamada de ferramenta (*tool-call*). Em modelos de *reasoning* locais (ex: Gemma 4), esse caminho truncaria o JSON do argumento e o endpoint o rejeitaria com um erro de `peg-gemma4 format` / saída malformada; retornar texto evita isso completamente.
- **`max_tokens`** (padrão `32768`) é enviado explicitamente em cada conclusão para que uma seção ou rascunho completo possa ser finalizado, em vez de ser cortado pelo padrão menor por requisição do LM Studio. O pipeline avisa se uma conclusão ainda parar por `length`, para que você saiba que deve aumentá-lo.
- **Fragmentação de seções (Chunking)** — quando a fonte excede `chunk_threshold_chars` (padrão `12000`) e `chunk_translation` é `true`, a fonte é dividida nos cabeçalhos Markdown de nível superior (`## `) (com consciência de blocos de código, para que `##` dentro de um bloco de código seja ignorado). Cada seção é traduzida em sua própria conclusão, e o orquestrador monta as peças e as salva. Nenhuma chamada única ao modelo precisa emitir o documento inteiro.
- **Revisão por seção** — com `review_sections` como `true` (o padrão), cada seção passa pelo mesmo ciclo de crítica $\rightarrow$ revisão que o caminho de etapa única utiliza, porém limitado àquela seção: o revisor compara a seção traduzida com sua fonte e o escritor revisa até que o revisor concorde (ou `MAX_ITERATIONS` seja atingido). Como a seção é pequena, a revisão e reescrita ficam longe do limite de truncamento que tornaria a revisão de um README grande insegura.

O caminho fragmentado deliberadamente **não** executa uma segunda revisão de todo o documento posteriormente — emitir novamente todo o README extenso em uma única conclusão reintroduziria o mesmo truncamento, e a passagem por seção já cobriu isso. Defina `review_sections` como `false` para traduzir documentos grandes sem qualquer revisão, ou `chunk_translation` como `false` para forçar o comportamento original de etapa única (que ainda executa o ciclo completo de revisão do documento inteiro). O caminho de etapa única abaixo do limite permanece inalterado.