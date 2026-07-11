# comprehend-markdown

*두루마리에 손을 얹고 주문을 외우십시오. 두루마리의 무게(문서의 양)에 따라 몇 분에서 한 시간 뒤, 당신은 어떤 언어로 작성된 마크다운이라도 완벽히 이해하게 될 것입니다.*

프로젝트의 `README.md`를 다른 언어로 번역하는 MCP 서버이자, 로컬 LM Studio 모델을 사용하여 작성자/검토자(writer/reviewer) 루프를 실행하는 독립형 파이프라인입니다.

소스 언어와 대상 언어는 모두 설정 가능하며, 영어는 기본값일 뿐입니다. `source_language`를 설정하여 중국어, 인도네시아어 또는 다른 언어에서 번역을 시작하고, `target_languages`를 통해 어떤 언어로 확장할지 선택하십시오 ([소스 및 대상 언어 선택](#소스-및-대상-언어-선택)).

대상 프로젝트에 대해 다음과 같은 구조를 기대하며(필요 시 자동 생성),

```
<project-root>/docs/<source>/README.md  표준 소스 (기본값: 영어)
<project-root>/docs/<lang>/README.md    언어별 번역 버전
<project-root>/README.md                언어 선택 랜딩 페이지 (자동 생성됨)
```

아직 마이그레이션되지 않아 소스가 루트에 있는 프로젝트도 작동합니다. 이 경우 루트의 `README.md`를 소스로 사용하며, `pipeline` 실행이 끝나면 해당 파일을 `docs/<source>/`(예: `docs/English/`)로 이동시키고, 사용 가능한 모든 번역본을 연결하는 짧은 랜딩 페이지를 루트 `README.md`로 생성합니다.

## 설정 (Setup)

가상 환경(venv) 생성 및 의존성 설치/동기화 등 모든 과정은 `run.sh`에서 처리되므로 별도의 설치 단계가 필요 없습니다. `requirements.txt`에서 패키지를 읽어 실행할 때마다 재설치하므로, 새로운 의존성을 반영하려면 다시 실행하기만 하면 됩니다.

기본값 외에 다른 로컬 LM Studio 모델을 사용하려면 예시 설정 파일을 복사하여 수정하십시오.

```bash
cp config.local.json.example config.local.json
```

`config.local.json`은 `.gitignore`에 등록되어 있으며 `config.json`의 설정을 키 단위로 덮어씁니다. 따라서 커밋된 기본값을 건드리지 않고 로컬에서 `lm_studio_url`, `model_name`, `api_key` 등을 조정할 수 있습니다.

### 소스 및 대상 언어 선택

두 개의 설정 키가 번역 방향을 제어하며, 서버와 파이프라인 모두 이 설정(`config.py`)을 읽으므로 서로 충돌하지 않습니다.

- **`source_language`** — 표준 `README.md`가 작성된 언어이자 `docs/<source_language>/` 폴더의 이름입니다. 기본값은 `"English"`입니다. 중국어(`"中文"`), 인도네시아어(`"Bahasa Indonesia"`) 등으로 설정하여 해당 언어를 소스로 사용할 수 있습니다.
- **`target_languages`** — 파이프라인이 번역을 수행할 대상 언어 목록입니다. `source_language`와 동일한 항목은 자동으로 건너뛰므로, 목록에 소스 언어가 포함되어 있어도 무방합니다.

예를 들어, 중국어 README를 영어와 스페인어로 번역하려면 다음과 같이 설정합니다.

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

`target_languages`가 생략되면 파이프라인에 내장된 18개 언어 목록을 사용합니다.

`api_key`는 LM Studio의 Developer 서버 설정에서 "Require API Key"를 활성화한 경우에만 필요합니다. 그렇지 않으면 LM Studio가 무시하는 `"lm-studio"`로 두십시오. 이는 LM Studio의 OpenAI 호환 엔드포인트를 직접 호출하는 `pipeline` 모드에만 적용됩니다. `serve` 모드는 MCP 클라이언트인 LM Studio가 서버를 호출하는 방식이므로 LM Studio API와 직접 통신하지 않습니다.

## 사용법 (Usage)

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCP 서버
./run.sh pipeline /absolute/path/to/project   # main.py 엔드-투-엔드 실행
```

두 모드 모두 번역할 `README.md`가 포함된 프로젝트 폴더의 **절대 경로**가 필요합니다. 터미널에서 대화형으로 실행하는 경우, `pipeline` 모드에서는 경로를 생략하고 나중에 입력할 수 있습니다.

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(`serve` 모드는 프롬프트를 띄우지 않습니다. 시작과 동시에 stdin/stdout이 MCP JSON-RPC 채널로 사용되며, MCP 호스트는 기본적으로 비대화형으로 서버를 실행하기 때문입니다.)

### `serve` — MCP 호스트 도구로 사용

MCP 호스트(예: LM Studio)가 서버의 `command`로 지정해야 할 모드이며, 대상 프로젝트의 절대 경로를 고정 인자로 전달합니다. 다음 기능을 제공합니다.

- **tool** `write_readme(language, content)` — `docs/<language>/README.md` 작성
- **tool** `write_directory_readme(content)` — 루트 `README.md`(언어 선택 랜딩 페이지) 작성
- **resource** `docs://readme` — 소스 파일 (`docs/<source_language>/README.md`, 없을 경우 루트 `README.md`)
- **resource** `docs://readme/{language}` — 기존 번역본 (있는 경우)
- **resource** `docs://dir_readme` — 루트 `README.md`
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — 신규 번역 루프
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — 업데이트 경로: 기존 번역본을 현재 소스와 비교하여 최소한의 변경 사항만 반영
- **prompt** `create_docs_language_directory` — 사용 가능한 번역 목록을 기반으로 루트 언어 선택 페이지 구축

호스트 자체 모델이 도구 호출(tool call)을 주도하며, 이 서버는 파일 I/O와 프롬프트 템플릿만을 제공합니다.

#### LM Studio에 추가하기

LM Studio의 MCP 설정은 `~/.lmstudio/mcp.json`에 위치합니다. 다음과 같이 항목을 추가하십시오.

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

두 번째 `args` 항목은 연결 시점에 고정됩니다. LM Studio의 설정은 정적 JSON이며 대화형 프롬프트를 지원하지 않으므로, 이 저장소의 경로가 아니라 실제로 번역하고자 하는 프로젝트의 경로를 입력해야 합니다.

### `pipeline` — 독립 실행 모드 (MCP 호스트 불필요)

설정된 `target_languages`(기본 18개 언어: Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — 목록이나 소스 언어를 변경하려면 [소스 및 대상 언어 선택](#소스-및-대상-언어-선택) 참조)에 대해 번역 $\rightarrow$ 비평 $\rightarrow$ 수정 루프를 직접 실행합니다.

작성자/검토자 단계마다 LM Studio의 OpenAI 호환 엔드포인트를 직접 호출하며, 파일 I/O를 위해 내부적으로 `server.py` 복사본을 stdio로 생성하여 사용합니다. LM Studio UI를 거치지 않고 일괄 번역할 때 유용합니다. 실행 시간은 로컬 모델과 문서 크기에 따라 달라집니다 (작은 README는 몇 분, 매우 큰 문서는 한 시간 정도 소요).

이미 `docs/<language>/README.md`가 존재하는 언어는 처음부터 다시 번역하지 않습니다. 검토자가 기존 번역본을 현재 소스와 비교하고, 변경 사항이 있는 경우에만 작성자가 최소한의 수정으로 패치합니다. 최신 상태인 번역본은 완전히 건너뛰므로, README 수정 후 파이프라인을 재실행하면 오래된 부분만 다시 작업합니다.

언어별 작업이 끝나면 (필요 시) 루트 수준의 소스 `README.md`를 `docs/<source_language>/`로 이동시키고, 모든 번역본을 연결하는 짧은 언어 선택 페이지를 루트 `README.md`로 재생성하며 마무리됩니다.

채팅 모델이 로드된 상태에서 LM Studio의 로컬 서버가 실행 중이어야 합니다 (`config.json` 참조). 파이프라인은 일반 텍스트 완성을 통해 모델을 구동하고 파일 쓰기는 직접 수행하므로, 모델이 OpenAI 스타일의 도구 호출(tool calls)을 지원할 필요는 없습니다 (아래 "대용량 README 처리" 섹션 참조). 전체 목록을 실행하기 전에 한 가지 언어로 먼저 테스트해 보는 것을 권장합니다.

### 대용량 README 처리

로컬 모델에서 대용량 README(예: `A-Starry-Sky` / `a-restless-ocean` 문서는 약 35~60 KB)를 단일 완성(completion)으로 번역하는 것은 신뢰성 측면에서 가장 큰 위험 요소입니다. 출력 토큰이나 컨텍스트가 부족해지면 뒷부분이 조용히 잘려 나갈 수 있습니다. `pipeline` 모드는 이를 방지하도록 설계되었습니다.

- **의도적인 Tool-free 설계.** 모델은 오직 일반 텍스트만 생성합니다. 모든 번역, 수정, 디렉토리 페이지는 응답 텍스트로 반환되며, 오케스트레이터가 서버의 `write_readme` / `write_directory_readme` 도구를 통해 직접 저장합니다. 모델이 전체 문서를 도구 호출 인자에 넣도록 요구하지 않습니다. Gemma 4와 같은 로컬 추론 모델에서 이 방식(도구 호출)을 사용하면 인자 JSON이 잘려 엔드포인트에서 `peg-gemma4 format` / malformed-output 오류가 발생하는데, 텍스트 반환 방식은 이를 완전히 회피합니다.
- **`max_tokens`** (기본값 `32768`)를 모든 완성 요청에 명시적으로 전송하여, LM Studio의 작은 기본값 때문에 끊기지 않고 섹션/초안 전체가 완료될 수 있도록 합니다. 그럼에도 불구하고 `length`로 인해 중단되면 파이프라인이 경고를 보내어 값을 높일 수 있게 안내합니다.
- **섹션 청킹 (Section chunking)** — 소스 길이가 `chunk_threshold_chars`(기본값 `12000`)를 초과하고 `chunk_translation`이 `true`인 경우, 최상위 마크다운 헤더(`## `)를 기준으로 소스를 분할합니다 (코드 블록 내부의 `##`는 무시함). 각 섹션은 개별 완성 요청으로 번역되며, 오케스트레이터가 이를 조립하여 저장합니다. 따라서 단일 모델 호출이 전체 문서를 출력해야 하는 상황이 발생하지 않습니다.
- **섹션별 검토 (Per-section review)** — `review_sections`가 `true`(기본값)인 경우, 각 섹션은 단일 샷 경로와 동일한 비평 $\rightarrow$ 수정 루프를 거칩니다. 다만 범위가 해당 섹션으로 한정됩니다. 검토자가 번역된 섹션을 소스와 비교하고 작성자가 수정하며, 합의에 도달하거나 `MAX_ITERATIONS`에 도달할 때까지 반복합니다. 섹션 단위는 크기가 작으므로 대용량 README 전체를 검토할 때 발생하는 절단 위험 없이 안전하게 수행됩니다.

청킹 경로에서는 이후에 전체 문서 검토를 다시 실행하지 않습니다. 대용량 README 전체를 다시 한 번의 완성으로 출력하면 동일한 절단 문제가 발생하며, 이미 섹션별 패스로 충분히 검토되었기 때문입니다. 리뷰 없이 대용량 문서를 번역하려면 `review_sections`를 `false`로 설정하고, 원래의 단일 샷 동작을 강제하려면 `chunk_translation`을 `false`로 설정하십시오 (이 경우 전체 문서 리뷰 루프가 실행됩니다). 임계값 이하의 단일 샷 경로는 기존과 동일하게 작동합니다.