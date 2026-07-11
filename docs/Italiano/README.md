# comprehend-markdown

*Sfiori la pergamena e pronunci l'incantesimo. Da pochi minuti a un'ora dopo (per documento, a seconda della mole del rotolo), comprenderai il Markdown in qualsiasi lingua.*

Un server MCP che traduce il `README.md` di un progetto in altre lingue, insieme a una pipeline indipendente che esegue un ciclo di scrittura e revisione utilizzando un modello locale di LM Studio.

Sia la lingua di origine che quelle di destinazione sono configurabili — l'inglese è solo il valore predefinito. Imposta `source_language` per tradurre *da* cinese, indonesiano o qualsiasi altra lingua, e `target_languages` per scegliere in quali lingue distribuire i contenuti (vedi [Scegliere le lingue di origine e di destinazione](#scegliere-le-lingue-di-origine-e-di-destinazione)).

Per ogni progetto di destinazione, il sistema si aspetta (e crea se necessario):

```
<project-root>/docs/<source>/README.md  la sorgente canonica (English per impostazione predefinita)
<project-root>/docs/<lang>/README.md    versioni tradotte, una per lingua
<project-root>/README.md                pagina di atterraggio per la scelta della lingua (generata)
```

Funziona anche per i progetti non ancora migrati — dove la sorgente si trova ancora nella root: il `README.md` principale viene usato come sorgente e, al termine dell'esecuzione della `pipeline`, viene spostato in `docs/<source>/` (ad es. `docs/English/`) e sostituito da una breve pagina di atterraggio generata che linka tutte le traduzioni disponibili.

## Setup

Tutto (creazione venv, installazione/sincronizzazione dipendenze) è gestito da `run.sh` — non è previsto un passaggio di installazione separato. Legge i pacchetti da `requirements.txt` e li reinstalla a ogni avvio, quindi per aggiornare le dipendenze basta eseguire nuovamente lo script.

Se desideri puntare a un modello locale di LM Studio diverso da quello predefinito, modifica i valori in `config.json`.

### Scegliere le lingue di origine e di destinazione

Due chiavi di configurazione in `config.json` controllano la direzione della traduzione:

- **`source_language`** — la lingua in cui è scritto il tuo `README.md` canonico e il nome della relativa cartella `docs/<source_language>/`. Il valore predefinito è `English`. Impostalo su `中文`, `Indonesia` o qualsiasi altra lingua per tradurre *da* quella lingua.
- **`target_languages`** — l'elenco delle lingue *in cui* la pipeline traduce. Qualsiasi voce coincidente con `source_language` viene saltata automaticamente, quindi lasciare la sorgente nell'elenco non causa problemi.

Per esempio, per tradurre un README cinese in inglese e spagnolo:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Se `target_languages` viene omesso, la pipeline utilizza l'elenco predefinito di 18 lingue.

`api_key` è rilevante solo se hai attivato "Require API Key" nelle impostazioni del server Developer di LM Studio — in caso contrario, lascialo come `"lm-studio"`, che LM Studio ignora. Nota che questo si applica solo alla modalità `pipeline`, l'unica parte che chiama direttamente l'endpoint compatibile con OpenAI di LM Studio; la modalità `serve` non comunica mai con l'API di LM Studio poiché è LM Studio stesso a essere il client MCP che la richiama.

È possibile impostare `max_tokens` qui, ma non è certo che LM Studio lo rispetti effettivamente. Assicurati di impostare questo valore ad almeno 24576 direttamente nel modello prima di eseguire lo script.

## Utilizzo

```bash
./run.sh serve    /percorso/assoluto/al/progetto   # server MCP stdio
./run.sh pipeline /percorso/assoluto/al/progetto   # esegue main.py end-to-end
```

Entrambe le modalità richiedono un percorso **assoluto** alla cartella del progetto contenente il `README.md` da tradurre. In modalità `pipeline` puoi ometterlo e inserirlo quando richiesto, a patto di eseguire il comando interattivamente in un terminale:

```bash
./run.sh pipeline
Enter absolute path to project folder: /percorso/assoluto/al/progetto
```

(La modalità `serve` non richiede input — una volta avviata, stdin/stdout diventano il canale JSON-RPC di MCP, e gli host MCP la lanciano comunque in modo non interattivo.)

### `serve` — come strumento per l'host MCP

Questo è il comando a cui un host MCP (ad es. LM Studio) deve puntare nel campo `command` del server, con il percorso assoluto del progetto di destinazione come argomento fisso. Espone:

- **tool** `write_readme(language, content)` — scrive `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — scrive il `README.md` principale (la pagina di scelta della lingua)
- **resource** `docs://readme` — la sorgente (`docs/<source_language>/README.md`, con fallback al `README.md` principale)
- **resource** `docs://readme/{language}` — la traduzione esistente, se presente
- **resource** `docs://dir_readme` — il `README.md` principale
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — il ciclo di nuova traduzione
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — il percorso di aggiornamento: confronta una traduzione esistente con la sorgente attuale e applica le modifiche minime necessarie
- **prompt** `create_docs_language_directory` — crea la pagina principale di scelta della lingua basandosi sull'elenco delle traduzioni disponibili

Il modello dell'host gestisce le chiamate agli strumenti; questo server fornisce solo l'I/O dei file e i template dei prompt.

#### Aggiungerlo a LM Studio

La configurazione MCP di LM Studio si trova in `~/.lmstudio/mcp.json`. Aggiungi una voce come questa:

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/percorso/assoluto/a/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/percorso/assoluto/al/progetto/che/vuoi/tradurre"
      ]
    }
  }
}
```

Il secondo elemento di `args` è fissato al momento della connessione — la configurazione di LM Studio è un JSON statico senza supporto per prompt interattivi, quindi deve essere il percorso effettivo del progetto che desideri tradurre, non il percorso di questo repository (a meno che quest'ultimo non sia proprio il progetto da tradurre).