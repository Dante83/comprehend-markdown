# comprehend-markdown

*Sfiori la pergamena e pronunci l'incantesimo. Dopo pochi minuti o un'ora (a seconda della mole del rotolo), comprenderai il Markdown in qualsiasi lingua.*

Un server MCP che traduce il `README.md` di un progetto in altre lingue, insieme a una pipeline standalone che esegue un ciclo di scrittura e revisione utilizzando un modello locale di LM Studio.

Sia la lingua di origine che quelle di destinazione sono configurabili — l'inglese è solo l'impostazione predefinita. Imposta `source_language` per tradurre *da* cinese, indonesiano o qualsiasi altra lingua, e `target_languages` per scegliere le lingue verso cui espandere la traduzione (vedi [Scegliere le lingue di origine e di destinazione](#scegliere-le-lingue-di-origine-e-di-destinazione)).

Per ogni progetto di destinazione, il sistema si aspetta (e crea se necessario):

```
<project-root>/docs/<source>/README.md  la sorgente canonica (predefinito: inglese)
<project-root>/docs/<lang>/README.md    versioni tradotte, una per lingua
<project-root>/README.md                pagina di atterraggio per la scelta della lingua (generata)
```

Funziona anche per i progetti non ancora migrati — dove la sorgente si trova ancora nella root: il `README.md` principale viene usato come sorgente e, al termine dell'esecuzione della `pipeline`, viene spostato in `docs/<source>/` (es. `docs/English/`) e sostituito da una breve pagina di atterraggio generata che linka tutte le traduzioni disponibili.

## Setup

Tutto (creazione venv, installazione/sincronizzazione delle dipendenze) è gestito da `run.sh` — non è previsto un passaggio di installazione separato. Legge i pacchetti da `requirements.txt` e li reinstalla a ogni avvio, quindi per aggiornare le dipendenze basta eseguire nuovamente lo script.

Se desideri puntare a un modello locale di LM Studio diverso da quello predefinito, copia l'esempio di configurazione e modificalo:

```bash
cp config.local.json.example config.local.json
```

`config.local.json` è inserito nel `.gitignore` e sovrascrive `config.json` chiave per chiave; puoi quindi regolare `lm_studio_url`, `model_name` o `api_key` localmente senza modificare i valori predefiniti condivisi nel repository.

### Scegliere le lingue di origine e di destinazione

Due chiavi di configurazione controllano la direzione della traduzione, e sia il server che la pipeline le leggono (da `config.py`), garantendo coerenza:

- **`source_language`** — la lingua in cui è scritto il tuo `README.md` canonico e il nome della relativa cartella `docs/<source_language>/`. Il valore predefinito è `"English"`. Impostalo su `"中文"`, `"Bahasa Indonesia"` o qualsiasi altra lingua per tradurre *da* quella lingua.
- **`target_languages`** — l'elenco delle lingue verso cui la pipeline effettua la traduzione. Qualsiasi voce coincidente con `source_language` viene saltata automaticamente, quindi lasciare la lingua di origine nell'elenco non causa problemi.

Per esempio, per tradurre un README cinese in inglese e spagnolo:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Se `target_languages` viene omesso, la pipeline utilizza l'elenco predefinito di 18 lingue.

La `api_key` è necessaria solo se hai attivato l'opzione "Require API Key" nelle impostazioni del server Developer di LM Studio — in caso contrario, lasciala come `"lm-studio"`, che viene ignorata da LM Studio. Nota che questo si applica solo alla modalità `pipeline`, l'unica parte che chiama direttamente l'endpoint compatibile con OpenAI di LM Studio; la modalità `serve` non comunica mai direttamente con l'API di LM Studio, poiché è LM Studio stesso a fungere da client MCP che la richiama.

## Utilizzo

```bash
./run.sh serve    /percorso/assoluto/al/progetto   # server MCP stdio
./run.sh pipeline /percorso/assoluto/al/progetto   # esegue main.py end-to-end
```

Entrambe le modalità richiedono un percorso **assoluto** alla cartella del progetto contenente il `README.md` da tradurre. In modalità `pipeline`, puoi ometterlo e inserirlo quando richiesto, a patto di eseguire il comando interattivamente in un terminale:

```bash
./run.sh pipeline
Enter absolute path to project folder: /percorso/assoluto/al/progetto
```

(La modalità `serve` non richiede input interattivi — una volta avviata, stdin/stdout diventano il canale JSON-RPC di MCP, e gli host MCP la lanciano comunque in modo non interattivo.)

### `serve` — come strumento per un host MCP

Questo è l'endpoint a cui un host MCP (es. LM Studio) deve puntare nel comando `command`, con il percorso assoluto del progetto target come argomento fisso. Espone:

- **tool** `write_readme(language, content)` — scrive il file `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — scrive il `README.md` nella root (la pagina di scelta della lingua)
- **resource** `docs://readme` — la sorgente (`docs/<source_language>/README.md`, o in alternativa il `README.md` nella root)
- **resource** `docs://readme/{language}` — la traduzione esistente, se presente
- **resource** `docs://dir_readme` — il `README.md` nella root
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — il ciclo di nuova traduzione
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — il percorso di aggiornamento: confronta una traduzione esistente con la sorgente attuale e applica le modifiche minime necessarie
- **prompt** `create_docs_language_directory` — crea la pagina di scelta della lingua nella root partendo dall'elenco delle traduzioni disponibili

Il modello dell'host gestisce le chiamate agli strumenti; questo server fornisce semplicemente l'I/O dei file e i template dei prompt.

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

Il secondo elemento di `args` è fissato al momento della connessione — la configurazione di LM Studio è un JSON statico senza supporto per prompt interattivi, quindi deve essere il percorso effettivo del progetto da tradurre (non il percorso di questo repository, a meno che non sia proprio quello il progetto target).

### `pipeline` — standalone, senza host MCP

Esegue autonomamente l'intero ciclo traduzione $\rightarrow$ critica $\rightarrow$ revisione per le lingue configurate in `target_languages` (elenco predefinito di 18: Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — vedi [Scegliere le lingue di origine e di destinazione](#scegliere-le-lingue-di-origine-e-di-destinazione) per modificare l'elenco o la lingua di origine), chiamando direttamente l'endpoint compatibile con OpenAI di LM Studio per i turni di scrittura/revisione e avviando una propria copia interna di `server.py` via stdio per gestire l'I/O dei file. Utile per traduzioni batch senza passare dall'interfaccia utente di LM Studio. I tempi di esecuzione variano in base alla dimensione del documento su un modello locale — pochi minuti per un README piccolo, fino a circa un'ora per uno molto voluminoso e suddiviso in blocchi.

Le lingue che hanno già un file `docs/<language>/README.md` non vengono ritradotte da zero: il revisore confronta la traduzione esistente con la sorgente attuale e, solo se qualcosa è cambiato, lo scrittore applica le correzioni minime. Le traduzioni aggiornate vengono saltate completamente, quindi rieseguire la pipeline dopo una modifica al README rigenererà solo le parti obsolete.

Al termine del lavoro per ogni lingua, l'esecuzione si conclude (se necessario) spostando il `README.md` sorgente dalla root a `docs/<source_language>/` e rigenerando il `README.md` della root come breve pagina di scelta della lingua che linka ogni traduzione non vuota.

Richiede che il server locale di LM Studio sia attivo (vedi `config.json`) con un modello chat caricato — la pipeline guida il modello tramite completamenti di testo semplice e gestisce autonomamente la scrittura dei file, quindi il modello **non** deve necessariamente supportare le chiamate a strumenti (tool calls) in stile OpenAI (vedi "Gestione README voluminosi" sotto). Si consiglia comunque di testare una singola lingua prima di avviare l'intera lista.

### Gestione README voluminosi

Tradurre un README di grandi dimensioni (i documenti fratelli `A-Starry-Sky` / `a-restless-ocean` sono circa 35–60 KB) in un unico completamento è il principale rischio di affidabilità con un modello locale: l'output potrebbe esaurire i token o il contesto a metà, troncando silenziosamente la parte finale. La modalità `pipeline` è progettata per evitare questo problema:

- **Assenza di tool per design.** Il modello produce solo testo semplice — ogni traduzione, riscrittura e pagina di directory viene restituita come risposta testuale, e l'orchestratore la salva tramite gli strumenti `write_readme` / `write_directory_readme` del server. Non viene mai chiesto al modello di inserire un intero documento all'interno dell'argomento di una tool-call. Sui modelli di *reasoning* locali (es. Gemma 4), quel percorso troncherebbe il JSON dell'argomento e l'endpoint restituirebbe un errore `peg-gemma4 format` / output malformato; restituire testo evita completamente questo problema.
- **`max_tokens`** (predefinito `32768`) viene inviato esplicitamente a ogni completamento, in modo che una sezione o una bozza completa possa essere terminata invece di essere tagliata dal valore predefinito per richiesta di LM Studio. La pipeline avvisa se un completamento si interrompe comunque per motivi di `length`, così saprai di dover aumentare il limite.
- **Suddivisione in sezioni (Chunking)** — quando la sorgente supera `chunk_threshold_chars` (predefinito `12000`) e `chunk_translation` è impostato su `true`, la sorgente viene suddivisa in base agli header Markdown di primo livello (`## `) (il sistema riconosce i blocchi di codice, quindi un `##` all'interno di un blocco di codice viene ignorato). Ogni sezione viene tradotta in un completamento separato e l'orchestratore assembla i pezzi prima di salvarli. Nessuna singola chiamata al modello deve emettere l'intero documento.
- **Revisione per sezione** — con `review_sections` impostato su `true` (predefinito), ogni sezione segue lo stesso ciclo critica $\rightarrow$ revisione del percorso a colpo singolo, ma limitatamente a quella sezione: il revisore confronta la sezione tradotta con la sua sorgente e lo scrittore la revisiona finché il revisore non è soddisfatto (o viene raggiunto il limite `MAX_ITERATIONS`). Poiché una sezione è piccola, la revisione e la riscrittura rimangono ben lontane dal limite di troncamento che renderebbe insicura la revisione dell'intero documento per un README voluminoso.

Il percorso suddiviso in blocchi **non** esegue deliberatamente una seconda revisione dell'intero documento alla fine — riemettere l'intero README voluminoso in un unico completamento reintrodurrebbe il problema del troncamento, e il passaggio per sezione lo ha già coperto. Imposta `review_sections` su `false` per tradurre documenti grandi senza alcuna revisione, oppure `chunk_translation` su `false` per forzare il comportamento originale a colpo singolo (che esegue comunque l'intero ciclo di revisione del documento). Il percorso a colpo singolo per i testi sotto la soglia rimane invariato.