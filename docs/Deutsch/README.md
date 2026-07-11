# comprehend-markdown

*Du berührst die Schriftrolle und sprichst die Beschwörung aus. Minuten oder eine Stunde später (je nach Umfang der Schriftrolle) verstehst du Markdown in jeder beliebigen Sprache.*

Ein MCP-Server, der die `README.md` eines Projekts in andere Sprachen übersetzt, sowie eine eigenständige Pipeline, die einen Writer/Reviewer-Loop mithilfe eines lokalen LM Studio-Modells darauf anwendet.

Sowohl die Quell- als auch die Zielsprachen sind konfigurierbar – Englisch ist lediglich der Standard. Setze `source_language`, um *aus* dem Chinesischen, Indonesischen oder einer anderen Sprache zu übersetzen, und `target_languages`, um festzulegen, in welche Sprachen das Dokument aufgeteilt werden soll (siehe [Quell- und Zielsprachen wählen](#quell-und-zielsprachen-wählen)).

Für jedes Zielprojekt werden folgende Strukturen erwartet (und bei Bedarf erstellt):

```
<project-root>/docs/<source>/README.md  die kanonische Quelle (standardmäßig Englisch)
<project-root>/docs/<lang>/README.md    übersetzte Versionen, eine pro Sprache
<project-root>/README.md                Landingpage zur Sprachauswahl (generiert)
```

Auch Projekte, die noch nicht migriert wurden – bei denen sich die Quelle noch im Root-Verzeichnis befindet –, funktionieren: Die `README.md` im Root wird als Quelle verwendet und am Ende eines `pipeline`-Durchlaufs in `docs/<source>/` verschoben (z. B. `docs/English/`) und durch eine kurze, generierte Landingpage ersetzt, die auf alle verfügbaren Übersetzungen verlinkt.

## Setup

Alles (Erstellung der venv, Installation/Synchronisation der Abhängigkeiten) wird über `run.sh` erledigt – es gibt keinen separaten Installationsschritt. Die Pakete werden aus der `requirements.txt` gelesen und bei jedem Start neu installiert; neue Abhängigkeiten werden also einfach durch einen erneuten Aufruf übernommen.

Wenn du auf ein anderes lokales LM Studio-Modell als das Standardmodell verweisen möchtest, kopiere die Beispielkonfiguration und bearbeite sie:

```bash
cp config.local.json.example config.local.json
```

`config.local.json` ist in der `.gitignore` hinterlegt und überschreibt `config.json` schlüsselweise. So kannst du `lm_studio_url`, `model_name` oder `api_key` lokal anpassen, ohne die committeden Standardwerte zu ändern.

### Quell- und Zielsprachen wählen

Zwei Konfigurationsschlüssel steuern die Übersetzungsrichtung. Sowohl der Server als auch die Pipeline lesen diese (aus `config.py`), sodass sie immer synchron bleiben:

- **`source_language`** — die Sprache, in der deine kanonische `README.md` geschrieben ist, und der Name des entsprechenden Ordners `docs/<source_language>/`. Standardmäßig `"English"`. Setze dies auf `"中文"`, `"Bahasa Indonesia"` oder eine andere Sprache, um *aus* dieser Sprache zu übersetzen.
- **`target_languages`** — die Liste der Sprachen, in die die Pipeline übersetzt. Einträge, die mit `source_language` identisch sind, werden automatisch übersprungen; es ist also unbedenklich, die Quellsprache in der Liste zu lassen.

Beispiel: Um eine chinesische README ins Englische und Spanische zu übersetzen:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Wenn `target_languages` weggelassen wird, greift die Pipeline auf eine integrierte Liste von 18 Sprachen zurück.

Der `api_key` ist nur relevant, wenn du in den Developer-Server-Einstellungen von LM Studio „Require API Key“ aktiviert hast – andernfalls lass ihn auf `"lm-studio"`, was von LM Studio ignoriert wird. Beachte, dass dies nur für den `pipeline`-Modus gilt, da dies der einzige Teil ist, der den OpenAI-kompatiblen Endpunkt von LM Studio direkt aufruft; der `serve`-Modus kommuniziert nicht selbst mit der API von LM Studio, da LM Studio hier der MCP-Client ist, der den Server aufruft.

## Nutzung

```bash
./run.sh serve    /absoluter/pfad/zum/projekt   # stdio MCP-Server
./run.sh pipeline /absoluter/pfad/zum/projekt   # führt main.py end-to-end aus
```

Beide Modi erfordern einen **absoluten** Pfad zum Projektordner, der die zu übersetzende `README.md` enthält. Im `pipeline`-Modus kannst du den Pfad weglassen und wirst stattdessen dazu aufgefordert, sofern du interaktiv in einem Terminal arbeitest:

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
- **prompt** `create_docs_language_directory` — erstellt die Root-Landingpage zur Sprachauswahl basierend auf den verfügbaren Übersetzungen

Das Modell des Hosts steuert die Tool-Aufrufe; dieser Server stellt lediglich die Datei-I/O und die Prompt-Templates bereit.

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

Der zweite Eintrag in `args` wird zum Zeitpunkt der Verbindung fixiert – die Konfiguration von LM Studio ist statisches JSON ohne Unterstützung für interaktive Prompts. Daher muss hier der tatsächliche Pfad des zu übersetzenden Projekts stehen, nicht der Pfad dieses Repositories (es sei denn, dies ist das Projekt, das du übersetzen möchtest).

### `pipeline` — eigenständig, ohne MCP-Host

Führt den vollständigen Loop aus Übersetzen → Kritisieren → Überarbeiten für die konfigurierten `target_languages` selbst aus (Standardliste von 18 Sprachen: Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — siehe [Quell- und Zielsprachen wählen](#quell-und-zielsprachen-wählen), um die Liste oder die Quellsprache zu ändern). Dabei wird der OpenAI-kompatible Endpunkt von LM Studio direkt für die Writer/Reviewer-Durchgänge aufgerufen, während eine interne Kopie von `server.py` über stdio für die Datei-I/O zuständig ist. Dies ist nützlich für Batch-Übersetzungen, ohne sie über das LM Studio UI steuern zu müssen. Die Laufzeit variiert je nach Dokumentgröße bei einem lokalen Modell – Minuten für eine kleine README, bis zu einer Stunde oder mehr für sehr große, in Abschnitte unterteilte Dokumente.

Sprachen, für die bereits eine `docs/<language>/README.md` existiert, werden nicht komplett neu übersetzt: Der Reviewer vergleicht die bestehende Übersetzung mit der aktuellen Quelle und nur wenn Änderungen vorliegen, patcht der Writer diese mit minimalen Korrekturen. Aktuelle Übersetzungen werden vollständig übersprungen, sodass ein erneuter Durchlauf nach einer Bearbeitung der README nur die veralteten Teile aktualisiert.

Nach der Bearbeitung pro Sprache wird der Durchlauf abgeschlossen, indem (falls nötig) eine `README.md` auf Root-Ebene nach `docs/<source_language>/` verschoben und die Root-`README.md` als kurze Sprachauswahlseite regeneriert wird, die auf alle nicht leeren Übersetzungen verlinkt.

Erfordert einen laufenden lokalen Server von LM Studio (siehe `config.json`) mit einem geladenen Chat-Modell – die Pipeline steuert das Modell über Plain-Text-Completions und übernimmt die Dateischreibvorgänge selbst. Das Modell muss daher **keine** OpenAI-style Tool-Calls unterstützen (siehe „Handling großer READMEs“ unten). Es empfiehlt sich dennoch, zuerst eine Sprache zu testen, bevor man einen vollständigen Durchlauf über die gesamte Liste startet.

### Handling großer READMEs

Die Übersetzung einer großen README (die beiden Beispiel-Dokumente `A-Starry-Sky` / `a-restless-ocean` sind ca. 35–60 KB) in einem einzigen Completion-Aufruf ist das größte Zuverlässigkeitsrisiko bei lokalen Modellen: Ihnen gehen mitten im Prozess die Output-Token oder der Kontext aus, und das Ende wird stillschweigend abgeschnitten. Der `pipeline`-Modus ist darauf ausgelegt, dies zu verhindern:

- **Tool-frei durch Design.** Das Modell erzeugt ausschließlich Plain Text – jede Übersetzung, Überarbeitung und Verzeichnisseite kommt als Antwort zurück, und der Orchestrator speichert sie selbst über die Tools `write_readme` / `write_directory_readme` des Servers. Es wird nie vom Modell verlangt, ein ganzes Dokument in ein Tool-Call-Argument zu pressen. Bei lokalen *Reasoning*-Modellen (z. B. Gemma 4) würde dieser Pfad das Argument-JSON abschneiden, was der Endpunkt mit einem `peg-gemma4 format` / malformed-output Fehler ablehnt; die Rückgabe als Text umgeht dies vollständig.
- **`max_tokens`** (Standard `32768`) wird bei jedem Completion-Aufruf explizit gesendet, damit ein ganzer Abschnitt/Entwurf fertiggestellt werden kann, anstatt am kleineren Standardwert von LM Studio abgeschnitten zu werden. Die Pipeline warnt, wenn eine Completion dennoch aufgrund der Länge (`length`) stoppt, damit du den Wert erhöhen kannst.
- **Abschnitts-Chunking** — Wenn die Quelle `chunk_threshold_chars` (Standard `12000`) überschreitet und `chunk_translation` auf `true` steht, wird die Quelle an Markdown-Überschriften der obersten Ebene (`## `) geteilt (unter Berücksichtigung von Code-Blöcken, sodass `##` innerhalb eines Blocks ignoriert wird). Jeder Abschnitt wird in einem eigenen Completion-Aufruf übersetzt, und der Orchestrator setzt die Teile zusammen und speichert sie. Kein einzelner Modellaufruf muss jemals das gesamte Dokument ausgeben.
- **Review pro Abschnitt** — Wenn `review_sections` auf `true` steht (Standard), durchläuft jeder Abschnitt denselben Kritik → Überarbeitungs-Loop wie der Single-Shot-Pfad, jedoch nur für diesen einen Abschnitt: Der Reviewer vergleicht den übersetzten Abschnitt mit seiner Quelle und der Writer überarbeitet ihn, bis der Reviewer zustimmt (oder `MAX_ITERATIONS` erreicht ist). Da ein Abschnitt klein ist, bleiben Review und Überarbeitung weit unter der Grenze zur Trunkierung, die eine Gesamtreview einer großen README unsicher machen würde.

Der Chunking-Pfad führt bewusst **keine** zweite Gesamtreview des gesamten Dokuments durch – das erneute Ausgeben der kompletten großen README in einem Aufruf würde dieselbe Trunkierung riskieren, und der pro-Abschnitt-Durchlauf hat dies bereits abgedeckt. Setze `review_sections` auf `false`, um große Dokumente ohne Review zu übersetzen, oder `chunk_translation` auf `false`, um das ursprüngliche Single-Shot-Verhalten zu erzwingen (welches weiterhin den vollständigen Gesamtreview-Loop ausführt). Der Single-Shot-Pfad unterhalb des Schwellenwerts bleibt unverändert.