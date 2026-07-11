# comprehend-markdown

*두루마리에 손을 얹고 주문을 외웁니다. 몇 분에서 한 시간 뒤(두루마리의 두께에 따라 다르지만), 당신은 어떤 언어로 쓰인 마크다운이라도 완벽히 이해하게 됩니다.*

프로젝트의 `README.md`를 다른 언어로 번역하는 MCP 서버이자, 로컬 LM Studio 모델을 사용하여 작성자/검토자 루프(writer/reviewer loop)를 실행하는 독립형 파이프라인입니다.

소스 언어와 대상 언어는 모두 설정 가능하며, 영어는 기본값일 뿐입니다. `source_language`를 설정하여 중국어, 인도네시아어 또는 다른 언어에서 번역을 시작하고, `target_languages`를 통해 어떤 언어로 확장할지 선택하세요 ([소스 및 대상 언어 선택](#소스-및-대상-언어-선택)).

대상 프로젝트에 대해 다음과 같은 구조를 기대하며(필요 시 자동 생성합니다):

```
<project-root>/docs/<source>/README.md  표준 소스 (기본값: 영어)
<project-root>/docs/<lang>/README.md    언어별 번역 버전
<project-root>/README.md                언어 선택 랜딩 페이지 (자동 생성됨)
```

아직 마이그레이션되지 않아 소스가 루트에 있는 프로젝트도 작동합니다. 이 경우 루트의 `README.md`를 소스로 사용하며, `pipeline` 실행이 끝나면 해당 파일을 `docs/<source>/`(예: `docs/English/`)로 이동시키고, 사용 가능한 모든 번역본으로 연결되는 짧은 랜딩 페이지를 루트에 생성하여 대체합니다.

## 설정 (Setup)

가상 환경(venv) 생성, 의존성 설치 및 동기화 등 모든 과정은 `run.sh`에서 처리되므로 별도의 설치 단계가 필요 없습니다. `requirements.txt`에서 패키지를 읽어와 실행할 때마다 재설치하므로, 새로운 의존성을 반영하려면 스크립트를 다시 실행하기만 하면 됩니다.

기본값 외에 다른 로컬 LM Studio 모델을 사용하려면 `config.json`의 값을 수정하세요.

### 소스 및 대상 언어 선택

`config.json`의 두 가지 설정 키가 번역 방향을 제어합니다:

- **`source_language`** — 표준 `README.md`가 작성된 언어이자, `docs/<source_language>/` 폴더의 이름이 됩니다. 기본값은 `English`입니다. 중국어(`中文`), 인도네시아어(`Indonesia`) 또는 다른 언어로 설정하여 해당 언어를 소스로 사용할 수 있습니다.
- **`target_languages`** — 파이프라인이 번역을 수행할 대상 언어 목록입니다. `source_language`와 동일한 항목은 자동으로 건너뛰므로, 목록에 소스 언어가 포함되어 있어도 무방합니다.

예를 들어, 중국어 README를 영어와 스페인어로 번역하려면 다음과 같이 설정합니다:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

`target_languages`를 생략하면 파이프라인에 내장된 18개 언어 목록을 기본으로 사용합니다.

`api_key`는 LM Studio의 Developer 서버 설정에서 "Require API Key"를 활성화한 경우에만 필요합니다. 그렇지 않으면 LM Studio가 무시하는 `"lm-studio"`로 두시면 됩니다. 이는 LM Studio의 OpenAI 호환 엔드포인트를 직접 호출하는 `pipeline` 모드에만 적용됩니다. `serve` 모드는 MCP 클라이언트인 LM Studio가 서버를 호출하는 방식이므로 LM Studio API와 직접 통신하지 않습니다.

`max_tokens` 설정이 가능하지만, LM Studio가 이를 실제로 준수하는지는 불분명합니다. 이 스크립트를 실행하기 전, 모델 자체 설정에서 이 값을 최소 24576 정도로 설정하시기 바랍니다.

## 사용법 (Usage)

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCP 서버
./run.sh pipeline /absolute/path/to/project   # main.py 엔드-투-엔드 실행
```

두 모드 모두 번역할 `README.md`가 포함된 프로젝트 폴더의 **절대 경로**가 필요합니다. 터미널에서 대화형으로 실행하는 경우, `pipeline` 모드에서는 경로를 생략하면 다음과 같이 입력 프롬프트가 나타납니다:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(`serve` 모드는 프롬프트를 띄우지 않습니다. 시작과 동시에 stdin/stdout이 MCP JSON-RPC 채널로 사용되며, MCP 호스트는 기본적으로 비대화형 방식으로 서버를 실행하기 때문입니다.)

### `serve` — MCP 호스트 도구로 사용하기

MCP 호스트(예: LM Studio)가 서버 `command`로 지정해야 할 모드이며, 대상 프로젝트의 절대 경로를 고정 인자로 전달합니다. 다음 기능을 제공합니다:

- **tool** `write_readme(language, content)` (README 작성) — `docs/<language>/README.md` 파일을 씁니다.
- **tool** `write_directory_readme(content)` (디렉토리 README 작성) — 루트의 `README.md`(언어 선택 랜딩 페이지)를 씁니다.
- **resource** `docs://readme` (README 리소스) — 소스 파일(`docs/<source_language>/README.md`, 없을 경우 루트 `README.md`)을 가져옵니다.
- **resource** `docs://readme/{language}` (언어별 README 리소스) — 기존 번역본이 있는 경우 이를 가져옵니다.
- **resource** `docs://dir_readme` (디렉토리 README 리소스) — 루트의 `README.md`를 가져옵니다.
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` (번역 루프) — 새로운 번역을 생성, 비평, 수정하는 루프입니다.
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` (업데이트 경로) — 기존 번역본을 현재 소스와 비교하여 최소한의 변경 사항만 반영해 패치합니다.
- **prompt** `create_docs_language_directory` (언어 디렉토리 생성) — 사용 가능한 번역 목록을 바탕으로 루트 언어 선택 페이지를 구축합니다.

호스트의 모델이 도구 호출(tool calls)을 주도하며, 이 서버는 파일 I/O와 프롬프트 템플릿만을 제공합니다.

#### LM Studio에 추가하기

LM Studio의 MCP 설정 파일은 `~/.lmstudio/mcp.json`에 위치합니다. 다음과 같이 항목을 추가하세요:

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

두 번째 `args` 항목은 연결 시점에 고정됩니다. LM Studio의 설정은 정적 JSON이며 대화형 프롬프트를 지원하지 않으므로, 이 저장소의 경로가 아니라 실제로 번역하고자 하는 프로젝트의 절대 경로를 입력해야 합니다.