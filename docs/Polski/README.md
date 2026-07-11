# comprehend-markdown

*Dotykasz zwoju i wypowiadasz inkantację. Kilka minut lub godzinę później (zależnie od grubości zwoju), rozumiesz Markdown w dowolnym języku.*

Serwer MCP, który tłumaczy plik `README.md` projektu na inne języki, oraz niezależny potok (pipeline), który uruchamia pętlę pisarz-recenzent przy użyciu lokalnego modelu LM Studio.

Język źródłowy i docelowe są konfigurowalne — angielski jest jedynie wartością domyślną. Ustaw `source_language`, aby tłumaczyć *z* języka chińskiego, indonezyjskiego lub dowolnego innego, oraz `target_languages`, aby wybrać języki docelowe (patrz: [Wybór języka źródłowego i docelowych](#wybór-języka-źródłowego-i-docelowych)).

Dla każdego projektu narzędzie oczekuje (i w razie potrzeby tworzy) następującą strukturę:

```
<project-root>/docs/<source>/README.md  kanoniczne źródło (domyślnie angielski)
<project-root>/docs/<lang>/README.md    wersje przetłumaczone, jedna na język
<project-root>/README.md                strona startowa z wyborem języka (generowana)
```

Projekt, który nie został jeszcze zmigrowany — gdzie źródło wciąż znajduje się w katalogu głównym — również będzie działać: główny plik `README.md` zostanie użyty jako źródło, a po zakończeniu działania `pipeline` zostanie on przeniesiony do `docs/<source>/` (np. `docs/English/`) i zastąpiony krótką, wygenerowaną stroną startową z linkami do wszystkich dostępnych tłumaczeń.

## Setup

Wszystko (tworzenie venv, instalacja/synchronizacja zależności) jest obsługiwane przez `run.sh` — nie ma osobnego kroku instalacji. Skrypt odczytuje pakiety z `requirements.txt` i reinstaluje je przy każdym uruchomieniu, więc pobranie nowych zależności sprowadza się do ponownego uruchomienia skryptu.

Jeśli chcesz wskazać inny lokalny model LM Studio niż domyślny, zmień wartości w pliku `config.json`.

### Wybór języka źródłowego i docelowych

Kierunek tłumaczenia w `config.json` kontrolują dwa klucze konfiguracyjne:

- **`source_language`** — język, w którym napisany jest kanoniczny plik `README.md`, oraz nazwa folderu `docs/<source_language>/`. Domyślnie ustawiony na `English`. Można go zmienić na `中文`, `Indonesia` lub dowolny inny, aby tłumaczyć *z* tego języka.
- **`target_languages`** — lista języków, na które potok tłumaczy treść. Każdy wpis identyczny z `source_language` jest automatycznie pomijany, więc pozostawienie źródła na liście nie powoduje problemów.

Przykład tłumaczenia chińskiego README na angielski i hiszpański:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Jeśli `target_languages` zostanie pominięte, potok skorzysta z wbudowanej listy 18 języków.

Klucz `api_key` ma znaczenie tylko wtedy, gdy w ustawieniach serwera deweloperskiego LM Studio włączono opcję „Require API Key” — w przeciwnym razie pozostaw go jako `"lm-studio"`, co LM Studio ignoruje. Należy pamiętać, że dotyczy to tylko trybu `pipeline`, który jest jedynym elementem bezpośrednio wywołującym endpoint LM Studio kompatybilny z OpenAI; tryb `serve` nigdy nie komunikuje się bezpośrednio z API LM Studio, ponieważ to LM Studio *jest* klientem MCP go wywołującym.

Dostępna jest opcja ustawienia `max_tokens`, jednak nie mam pewności, czy LM Studio faktycznie go respektuje. Przed uruchomieniem skryptu upewnij się, że w samym modelu wartość ta jest ustawiona na co najmniej około 24576.

## Użycie

```bash
./run.sh serve    /absolute/path/to/project   # serwer MCP stdio
./run.sh pipeline /absolute/path/to/project   # uruchamia main.py end-to-end
```

Oba tryby wymagają **bezwzględnej** ścieżki do folderu projektu zawierającego `README.md` do tłumaczenia. W trybie `pipeline` można pominąć ścieżkę i zostać o nią zapytanym, pod warunkiem uruchomienia skryptu interaktywnie w terminalu:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(Tryb `serve` nigdy nie prosi o dane — po uruchomieniu stdin/stdout stają się kanałem JSON-RPC dla MCP, a hosty MCP i tak uruchamiają go w sposób nieinteraktywny).

### `serve` — jako narzędzie hosta MCP

Jest to tryb, na który host MCP (np. LM Studio) powinien wskazać w polu `command`, podając bezwzględną ścieżkę do projektu docelowego jako stały argument. Udostępnia on:

- **tool** `write_readme(language, content)` — zapisuje plik `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — zapisuje główny plik `README.md` (stronę wyboru języka)
- **resource** `docs://readme` — źródło (`docs/<source_language>/README.md`, ewentualnie główny `README.md`)
- **resource** `docs://readme/{language}` — istniejące tłumaczenie, jeśli istnieje
- **resource** `docs://dir_readme` — główny plik `README.md`
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — pętla nowego tłumaczenia
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — ścieżka aktualizacji: porównanie istniejącego tłumaczenia z obecnym źródłem i naniesienie minimalnych poprawek
- **prompt** `create_docs_language_directory` — budowa głównej strony wyboru języka na podstawie listy dostępnych tłumaczeń

Model hosta steruje wywołaniami narzędzi; ten serwer zapewnia jedynie operacje wejścia/wyjścia plików oraz szablony promptów.

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

Drugi wpis w `args` jest stały w momencie połączenia — konfiguracja LM Studio to statyczny plik JSON bez obsługi interaktywnych promptów, więc musi to być rzeczywista ścieżka do projektu, który chcesz przetłumaczyć (chyba że chcesz przetłumaczyć repozytorium tego narzędzia).