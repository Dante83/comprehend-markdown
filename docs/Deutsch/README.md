# comprehend-markdown

*Du berührst die Schriftrolle und sprichst den Zauberspruch. Minuten bis eine Stunde später (je nach Umfang der Rolle) verstehst du Markdown in jeder beliebigen Sprache.*

Ein MCP-Server, der die `README.md` eines Projekts in andere Sprachen übersetzt, sowie eine eigenständige Pipeline, die einen Writer/Reviewer-Loop mithilfe eines lokalen LM Studio-Modells darauf anwendet.

Sowohl die Quell- als auch die Zielsprachen sind konfigurierbar – Englisch ist lediglich der Standard. Setze `source_language`, um *aus* dem Chinesischen, Indonesischen oder einer anderen Sprache zu übersetzen, und `target_languages`, um festzulegen, in welche Sprachen das Dokument aufgeteilt werden soll (siehe [Auswahl der Quell- und Zielsprachen](#auswahl-der-quell-und-zielsprachen)).

Für jedes Zielprojekt werden folgende Dateien erwartet (und bei Bedarf erstellt):

```
<project-root>/docs/<source>/README.md  die kanonische Quelle (standardmäßig Englisch)
<project-root>/docs/<lang>/README.md    übersetzte Versionen, eine pro Sprache
<project-root>/README.md                Landingpage zur Sprachauswahl (generiert)
```

Auch Projekte, die noch nicht migriert wurden – bei denen sich die Quelle noch im Root-Verzeichnis befindet –, funktionieren: Die `README.md` im Root wird als Quelle verwendet und am Ende eines `pipeline`-Durchlaufs in `docs/<source>/` verschoben (z. B. `docs/English/`) und durch eine kurze, generierte Landingpage ersetzt, die auf alle verfügbaren Übersetzungen verlinkt.

## Setup

Alles (Erstellung der venv, Installation/Synchronisierung der Abhängigkeiten) wird über `run.sh` erledigt – es gibt keinen separaten Installationsschritt. Die Pakete werden aus der `requirements.txt` gelesen und bei jedem Start neu installiert; neue Abhängigkeiten zu laden bedeutet also einfach, das Skript erneut auszuführen.

Wenn du auf ein anderes lokales LM Studio-Modell als das Standardmodell verweisen möchtest, ändere die Werte in der `config.json`.

### Auswahl der Quell- und Zielsprachen

Zwei Konfigurationsschlüssel in der `config.json` steuern die Übersetzungsrichtung:

- **`source_language`** — die Sprache, in der deine kanonische `README.md` geschrieben ist, sowie der Name des entsprechenden Ordners `docs/<source_language>/`. Standardmäßig `English`. Setze diesen Wert auf `中文`, `Indonesia` oder eine andere Sprache, um *aus* dieser Sprache zu übersetzen.
- **`target_languages`** — die Liste der Sprachen, in die die Pipeline übersetzt. Jeder Eintrag, der mit `source_language` identisch ist, wird automatisch übersprungen; es ist also unbedenklich, die Quellsprache in der Liste zu lassen.

Beispiel: Um eine chinesische README ins Englische und Spanische zu übersetzen:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Wenn `target_languages` weggelassen wird, greift die Pipeline auf eine integrierte Liste von 18 Sprachen zurück.

Der `api_key` ist nur relevant, wenn du in den Developer-Server-Einstellungen von LM Studio „Require API Key“ aktiviert hast – ansonsten lass ihn auf `"lm-studio"`, was von LM Studio ignoriert wird. Beachte, dass dies nur für den `pipeline`-Modus gilt, da dies der einzige Teil ist, der direkt den OpenAI-kompatiblen Endpunkt von LM Studio aufruft; der `serve`-Modus kommuniziert nie direkt mit der API von LM Studio, da LM Studio selbst der MCP-Client ist, der ihn aufruft.

`max_tokens` kann hier konfiguriert werden, allerdings ist unklar, ob LM Studio dies tatsächlich beachtet. Stelle sicher, dass du im Modell selbst einen Wert von mindestens etwa 24576 einstellst, bevor du dieses Skript ausführst.

## Nutzung

```bash
./run.sh serve    /absoluter/pfad/zum/projekt   # stdio MCP-Server
./run.sh pipeline /absoluter/pfad/zum/projekt   # führt main.py end-to-end aus
```

Beide Modi erfordern einen **absoluten** Pfad zum Projektordner, der die zu übersetzende `README.md` enthält. Im `pipeline`-Modus kannst du diesen weglassen und wirst stattdessen dazu aufgefordert, sofern du interaktiv in einem Terminal arbeitest:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absoluter/pfad/zum/projekt
```

(Der `serve`-Modus fragt nie nach – sobald er startet, dienen stdin/stdout als MCP JSON-RPC-Kanal, und MCP-Hosts starten ihn ohnehin nicht interaktiv.)

### `serve` — als MCP-Host-Tool

Dies ist der Befehl, auf den ein MCP-Host (z. B. LM Studio) in seinem Server-`command` verweisen sollte, wobei der absolute Pfad zum Zielprojekt als festes Argument übergeben wird. Es stellt Folgendes bereit:

- **tool** `write_readme(language, content)` — schreibt die Datei `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — schreibt die Root-`README.md` (die Sprachauswahl-Landingpage)
- **resource** `docs://readme` — die Quelle (`docs/<source_language>/README.md`, alternativ die Root-`README.md`)
- **resource** `docs://readme/{language}` — die bestehende Übersetzung, falls vorhanden
- **resource** `docs://dir_readme` — die Root-`README.md`
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — der Loop für Neuübersetzungen
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — der Update-Pfad: Vergleicht eine bestehende Übersetzung mit der aktuellen Quelle und patcht sie mit minimalen Änderungen
- **prompt** `create_docs_language_directory` — erstellt die Root-Sprachauswahlseite basierend auf der Liste der verfügbaren Übersetzungen

Das Modell des Hosts steuert die Tool-Aufrufe; dieser Server stellt lediglich den Datei-I/O und die Prompt-Templates bereit.

#### Integration in LM Studio

Die MCP-Konfiguration von LM Studio befindet sich unter `~/.lmstudio/mcp.json`. Füge einen Eintrag wie diesen hinzu:

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/absoluter/pfad/zu/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/absoluter/pfad/zum/projekt/das/übersetzt/werden/soll"
      ]
    }
  }
}
```

Der zweite Eintrag in `args` wird zum Zeitpunkt der Verbindung fixiert – die Konfiguration von LM Studio ist statisches JSON ohne Unterstützung für interaktive Abfragen. Daher muss dies der tatsächliche Pfad des zu übersetzenden Projekts sein, nicht der Pfad dieses Repositories (es sei denn, das Repository selbst ist das Projekt, das du übersetzen möchtest).