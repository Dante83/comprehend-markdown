# comprehend-markdown

*Dotykasz zwoju i wypowiadasz inkantację. Po kilku minutach lub godzinie (zależnie od ciężaru zwoju), zaczynasz rozumieć Markdown w dowolnym języku.*

Serwer MCP, który tłumaczy plik `README.md` projektu na inne języki, oraz niezależny pipeline, który uruchamia pętlę pisarz/recenzent (writer/reviewer loop) przy użyciu lokalnego modelu LM Studio.

Język źródłowy i docelowe są konfigurowalne — angielski jest jedynie wartością domyślną. Ustaw `source_language`, aby tłumaczyć *z* języka chińskiego, indonezyjskiego lub dowolnego innego, oraz `target_languages`, aby wybrać języki docelowe (patrz: [Wybór języka źródłowego i docelowych](#wybór-języka-źródłowego-i-docelowych)).

Dla każdego projektu narzędzie oczekuje (i w razie potrzeby tworzy) następującą strukturę:

```
<project-root>/docs/<source>/README.md  kanoniczne źródło (domyślnie angielski)
<project-root>/docs/<lang>/README.md    wersje przetłumaczone, jedna na język
<project-root>/README.md                strona powitalna z wyborem języka (generowana)
```

Projekt, który nie został jeszcze zmigrowany — gdzie źródło wciąż znajduje się w katalogu głównym — również będzie działać: główny plik `README.md` zostanie użyty jako źródło, a po zakończeniu działania `pipeline` zostanie on przeniesiony do `docs/<source>/` (np. `docs/English/`) i zastąpiony krótką, wygenerowaną stroną powitalną z linkami do wszystkich dostępnych tłumaczeń.

## Setup

Wszystko (tworzenie venv, instalacja/synchronizacja zależności) jest obsługiwane przez `run.sh` — nie ma osobnego kroku instalacji. Skrypt odczytuje pakiety z `requirements.txt` i reinstaluje je przy każdym uruchomieniu, więc pobranie nowych zależności sprowadza się do ponownego uruchomienia skryptu.

Jeśli chcesz wskazać lokalny model LM Studio inny niż domyślny, skopiuj przykładową konfigurację i edytuj ją:

```bash
cp config.local.json.example config.local.json
```

Plik `config.local.json` jest zignorowany przez git i nadpisuje klucze w `config.json`, dzięki czemu możesz lokalnie dostosować `lm_studio_url` / `model_name` / `api_key` bez modyfikowania domyślnych ustawień w repozytorium.

### Wybór języka źródłowego i docelowych

Kierunek tłumaczenia kontrolują dwa klucze konfiguracyjne, które są odczytywane zarówno przez serwer, jak i pipeline (z `config.py`), dzięki czemu są one zawsze spójne:

- **`source_language`** — język, w którym napisany jest kanoniczny plik `README.md`, oraz nazwa folderu `docs/<source_language>/`. Domyślnie `"English"`. Ustaw na `"中文"`, `"Bahasa Indonesia"` lub dowolny inny, aby tłumaczyć *z* tego języka.
- **`target_languages`** — lista języków, na które pipeline tłumaczy tekst. Każdy wpis równy `source_language` jest automatycznie pomijany, więc pozostawienie źródła na liście jest bezpieczne.

Na przykład, aby przetłumaczyć chiński README na angielski i hiszpański:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Jeśli `target_languages` zostanie pominięte, pipeline skorzysta z wbudowanej listy 18 języków.

Klucz `api_key` ma znaczenie tylko wtedy, gdy w ustawieniach serwera deweloperskiego LM Studio włączono opcję "Require API Key" — w przeciwnym razie pozostaw go jako `"lm-studio"`, co LM Studio ignoruje. Należy pamiętać, że dotyczy to tylko trybu `pipeline`, który jest jedynym elementem bezpośrednio wywołującym endpoint LM Studio kompatybilny z OpenAI; tryb `serve` nigdy nie komunikuje się bezpośrednio z API LM Studio, ponieważ to LM Studio *jest* klientem MCP wywołującym serwer.

## Użycie

```bash
./run.sh serve    /absolute/path/to/project   # serwer MCP stdio
./run.sh pipeline /absolute/path/to/project   # uruchamia main.py end-to-end
```

Oba tryby wymagają **bezwzględnej** ścieżki do folderu projektu zawierającego `README.md` do tłumaczenia. W trybie `pipeline` można ją pominąć — wtedy zostaniesz o nią zapytany, pod warunkiem że uruchamiasz program interaktywnie w terminalu:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(Tryb `serve` nigdy nie prosi o dane — po uruchomieniu stdin/stdout stają się kanałem JSON-RPC dla MCP, a hosty MCP i tak uruchamiają go w sposób nieinteraktywny).

### `serve` — jako narzędzie hosta MCP

Jest to tryb, na który powinien wskazywać parametr `command` w konfiguracji serwera hosta MCP (np. LM Studio), z bezwzględną ścieżką do projektu docelowego jako stałym argumentem. Udostępnia on:

- **tool** `write_readme(language, content)` — zapisuje plik `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — zapisuje główny plik `README.md` (strona wyboru języka)
- **resource** `docs://readme` — źródło (`docs/<source_language>/README.md`, ewentualnie główny `README.md`)
- **resource** `docs://readme/{language}` — istniejące tłumaczenie, jeśli istnieje
- **resource** `docs://dir_readme` — główny plik `README.md`
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — pętla nowego tłumaczenia
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — ścieżka aktualizacji: porównanie istniejącego tłumaczenia z obecnym źródłem i naniesienie minimalnych poprawek
- **prompt** `create_docs_language_directory` — budowanie głównej strony wyboru języka na podstawie listy dostępnych tłumaczeń

To model hosta steruje wywołaniami narzędzi; ten serwer zapewnia jedynie operacje wejścia/wyjścia plików i szablony promptów.

#### Dodawanie do LM Studio

Konfiguracja MCP w LM Studio znajduje się w `~/.lmstudio/mcp.json`. Dodaj wpis w następujący sposób:

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

Drugi wpis w `args` jest stały w momencie połączenia — konfiguracja LM Studio to statyczny plik JSON bez obsługi interaktywnych promptów, więc musi to być rzeczywista ścieżka do projektu, który chcesz przetłumaczyć (a nie ścieżka do tego repozytorium, chyba że to ono jest projektem docelowym).

### `pipeline` — samodzielny, bez hosta MCP

Samodzielnie uruchamia pełną pętlę tłumaczenie $\rightarrow$ krytyka $\rightarrow$ poprawka dla skonfigurowanych `target_languages` (domyślna lista 18 języków: Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — patrz [Wybór języka źródłowego i docelowych](#wybór-języka-źródłowego-i-docelowych), aby zmienić listę lub język źródłowy). Wywołuje bezpośrednio endpoint LM Studio kompatybilny z OpenAI dla etapów pisania/recenzowania i uruchamia wewnętrzną kopię `server.py` przez stdio do obsługi plików. Przydatne do masowego tłumaczenia bez konieczności korzystania z interfejsu użytkownika LM Studio. Czas wykonania zależy od rozmiaru dokumentu przy modelu lokalnym — od kilku minut dla małego README, do około godziny dla dużego pliku podzielonego na części.

Języki, które mają już plik `docs/<language>/README.md`, nie są tłumaczone od zera: recenzent porównuje istniejące tłumaczenie z obecnym źródłem i tylko w przypadku wykrycia zmian pisarz nanosi minimalne poprawki. Aktualne tłumaczenia są całkowicie pomijane, więc ponowne uruchomienie pipeline'u po edycji README przetwarza tylko nieaktualne części.

Po zakończeniu prac nad poszczególnymi językami, proces kończy się (jeśli jest to konieczne) przeniesieniem głównego pliku źródłowego `README.md` do `docs/<source_language>/` i ponownym wygenerowaniem głównego pliku `README.md` jako krótkiej strony wyboru języka linkującej do każdego niepustego tłumaczenia.

Wymaga uruchomionego lokalnego serwera LM Studio (patrz `config.json`) z załadowanym dowolnym modelem czatu — pipeline steruje modelem za pomocą zwykłych uzupełnień tekstu (plain text completions) i sam zapisuje pliki, więc model **nie musi** obsługiwać wywołań narzędzi w stylu OpenAI (patrz "Obsługa dużych plików README" poniżej). Mimo to warto przetestować jeden język przed uruchomieniem pełnego procesu dla całej listy.

### Obsługa dużych plików README

Tłumaczenie dużego pliku README (dokumentacja `A-Starry-Sky` / `a-restless-ocean` ma ok. 35–60 KB) w ramach jednego uzupełnienia tekstu jest głównym ryzykiem niezawodności przy modelu lokalnym: modelowi może zabraknąć tokenów wyjściowych lub kontekstu w połowie procesu, co prowadzi do cichego ucięcia końcówki tekstu. Tryb `pipeline` został zaprojektowany tak, aby tego uniknąć:

- **Z założenia bez użycia narzędzi (tool-free).** Model generuje wyłącznie zwykły tekst — każde tłumaczenie, poprawka i strona katalogu wracają jako odpowiedź, a orchestrator zapisuje je samodzielnie za pomocą narzędzi `write_readme` / `write_directory_readme`. Nic nie wymaga od modelu wpychania całego dokumentu do argumentu wywołania narzędzia. W lokalnych modelach rozumujących (np. Gemma 4) taka ścieżka ucina JSON argumentu, a endpoint odrzuca go z błędem `peg-gemma4 format` / malformed-output; zwracanie tekstu całkowicie omija ten problem.
- **`max_tokens`** (domyślnie `32768`) jest przesyłane jawnie przy każdym uzupełnieniu, aby pełna sekcja/szkic mogła zostać ukończona zamiast zostać ucięta przez mniejszy domyślny limit LM Studio na żądanie. Pipeline ostrzega, jeśli uzupełnienie nadal zatrzymało się z powodu długości (`length`), abyś wiedział, że należy zwiększyć ten limit.
- **Podział na sekcje (chunking)** — gdy źródło przekracza `chunk_threshold_chars` (domyślnie `12000`) i `chunk_translation` jest ustawione na `true`, źródło jest dzielone według nagłówków Markdown najwyższego poziomu (`## `) (z uwzględnieniem bloków kodu, więc `##` wewnątrz bloku kodu pozostaje nienaruszone). Każda sekcja jest tłumaczona w osobnym zapytaniu, a orchestrator składa części i zapisuje je. Żadne pojedyncze wywołanie modelu nie musi emitować całego dokumentu.
- **Recenzja per sekcja** — przy ustawieniu `review_sections` na `true` (domyślnie), każda sekcja przechodzi tę samą pętlę krytyka $\rightarrow$ poprawka, co w przypadku pojedynczego przejścia, ale ograniczoną do tej jednej sekcji: recenzent porównuje przetłumaczoną sekcję z jej źródłem, a pisarz ją poprawia, aż recenzent zaakceptuje wynik (lub zostanie osiągnięta liczba `MAX_ITERATIONS`). Ponieważ sekcja jest mała, proces recenzji i poprawiania pozostaje bezpiecznie poniżej limitu ucięcia tekstu, który sprawiał, że recenzja całego dużego README była ryzykowna.

Ścieżka z podziałem na części celowo **nie uruchamia** drugiej, pełnej recenzji całego dokumentu na koniec — ponowne wygenerowanie całego dużego README w jednym zapytaniu przywróciłoby problem ucinania tekstu, a przejście per sekcja już to pokryło. Ustaw `review_sections` na `false`, aby tłumaczyć duże dokumenty bez recenzji, lub `chunk_translation` na `false`, aby wymusić oryginalne zachowanie pojedynczego przejścia (które wciąż uruchamia pełną pętlę recenzji całego dokumentu). Ścieżka pojedynczego przejścia dla plików poniżej progu pozostaje bez zmian.