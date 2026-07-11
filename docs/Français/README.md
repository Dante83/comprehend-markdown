# comprehend-markdown

*Vous effleurez le parchemin et prononcez l'incantation. Quelques minutes ou une heure plus tard (selon le poids du grimoire), vous comprenez le Markdown dans n'importe quelle langue.*

Un serveur MCP qui traduit le fichier `README.md` d'un projet vers d'autres langues, accompagné d'un pipeline autonome qui exécute une boucle de rédaction et de révision via un modèle local LM Studio.

La langue source et les langues cibles sont configurables — l'anglais n'est que la valeur par défaut. Réglez `source_language` pour traduire *depuis* le chinois, l'indonésien ou toute autre langue, et `target_languages` pour choisir les langues de destination (voir [Choisir les langues source et cible](#choisir-les-langues-source-et-cible)).

Pour tout projet cible, l'outil s'attend à trouver (et crée si nécessaire) la structure suivante :

```
<project-root>/docs/<source>/README.md  la source canonique (anglais par défaut)
<project-root>/docs/<lang>/README.md    les versions traduites, une par langue
<project-root>/README.md                page d'accueil de sélection de langue (générée)
```

Les projets qui n'ont pas encore été migrés — où la source se trouve toujours à la racine — sont également pris en charge : le `README.md` racine est utilisé comme source et, à la fin de l'exécution du `pipeline`, il est déplacé vers `docs/<source>/` (ex: `docs/English/`) et remplacé par une courte page d'accueil générée qui lie toutes les traductions disponibles.

## Installation

Tout (création du venv, installation/synchronisation des dépendances) est géré par `run.sh` — il n'y a pas d'étape d'installation séparée. Il lit les paquets depuis `requirements.txt` et les réinstalle à chaque exécution ; ainsi, pour récupérer de nouvelles dépendances, il suffit de le relancer.

Si vous souhaitez utiliser un modèle LM Studio local autre que celui par défaut, copiez l'exemple de configuration et modifiez-le :

```bash
cp config.local.json.example config.local.json
```

Le fichier `config.local.json` est ignoré par git et surcharge les clés de `config.json`, vous permettant ainsi d'ajuster `lm_studio_url`, `model_name` ou `api_key` localement sans modifier les valeurs par défaut commitées.

### Choisir les langues source et cible

Deux clés de configuration contrôlent la direction de la traduction, et le serveur ainsi que le pipeline les lisent tous deux (depuis `config.py`), garantissant ainsi leur cohérence :

- **`source_language`** — la langue dans laquelle votre `README.md` canonique est écrit, et le nom de son dossier `docs/<source_language>/`. Par défaut : `"English"`. Réglez-le sur `"中文"`, `"Bahasa Indonesia"` ou toute autre langue pour traduire *depuis* celle-ci.
- **`target_languages`** — la liste des langues vers lesquelles le pipeline traduit. Toute entrée identique à `source_language` est automatiquement ignorée, il est donc sans danger de laisser la source dans la liste.

Par exemple, pour traduire un README chinois vers l'anglais et l'espagnol :

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Si `target_languages` est omis, le pipeline utilise sa liste intégrée de 18 langues.

La clé `api_key` n'est utile que si vous avez activé l'option "Require API Key" dans les paramètres du serveur Developer de LM Studio — sinon, laissez-la sur `"lm-studio"`, valeur ignorée par LM Studio. Notez que cela ne s'applique qu'au mode `pipeline`, qui est la seule partie appelant directement le point de terminaison compatible OpenAI de LM Studio ; le mode `serve` ne communique jamais avec l'API de LM Studio car c'est LM Studio lui-même qui agit comme client MCP pour l'appeler.

## Utilisation

```bash
./run.sh serve    /chemin/absolu/vers/projet   # serveur MCP stdio
./run.sh pipeline /chemin/absolu/vers/projet   # exécute main.py de bout en bout
```

Les deux modes nécessitent un chemin **absolu** vers le dossier du projet contenant le `README.md` à traduire. En mode `pipeline`, vous pouvez omettre ce chemin et le saisir lors de l'invite, à condition d'exécuter la commande interactivement dans un terminal :

```bash
./run.sh pipeline
Enter absolute path to project folder: /chemin/absolu/vers/projet
```

(Le mode `serve` ne propose jamais d'invite — une fois lancé, l'entrée et la sortie standard deviennent le canal JSON-RPC de MCP, et les hôtes MCP le lancent de toute façon de manière non interactive.)

### `serve` — en tant qu'outil pour hôte MCP

C'est ce point que doit viser la commande `command` d'un hôte MCP (ex: LM Studio), avec le chemin absolu du projet cible comme argument fixe. Il expose :

- **tool** `write_readme(language, content)` — écrit le fichier `docs/<language>/README.md`.
- **tool** `write_directory_readme(content)` — écrit le `README.md` racine (la page de sélection de langue).
- **resource** `docs://readme` — la source (`docs/<source_language>/README.md`, ou le `README.md` racine par défaut).
- **resource** `docs://readme/{language}` — la traduction existante, le cas échéant.
- **resource** `docs://dir_readme` — le `README.md` racine.
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — la boucle de traduction initiale.
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — le flux de mise à jour : compare une traduction existante avec la source actuelle et y apporte des corrections minimales.
- **prompt** `create_docs_language_directory` — génère la page racine de sélection de langue à partir de la liste des traductions disponibles.

Le modèle de l'hôte pilote les appels d'outils ; ce serveur ne fournit que les entrées/sorties de fichiers et les modèles de prompts.

#### Ajout à LM Studio

La configuration MCP de LM Studio se trouve dans `~/.lmstudio/mcp.json`. Ajoutez une entrée telle que :

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/chemin/absolu/vers/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/chemin/absolu/vers/le/projet/que/vous/voulez/traduire"
      ]
    }
  }
}
```

Le second argument dans `args` est fixé lors de la connexion — la configuration de LM Studio étant un JSON statique sans support d'invite interactive, il doit s'agir du chemin réel du projet à traduire, et non du chemin de ce dépôt (sauf si c'est ce projet que vous souhaitez traduire).

### `pipeline` — autonome, sans hôte MCP

Exécute lui-même la boucle complète traduction $\rightarrow$ critique $\rightarrow$ révision pour les `target_languages` configurées (liste par défaut de 18 langues : Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — voir [Choisir les langues source et cible](#choisir-les-langues-source-et-cible) pour modifier la liste ou la langue source).

Il appelle directement le point de terminaison compatible OpenAI de LM Studio pour les phases de rédaction/révision et lance sa propre copie interne de `server.py` via stdio pour gérer les fichiers. C'est utile pour des traductions par lots sans passer par l'interface utilisateur de LM Studio. Le temps d'exécution varie selon la taille du document sur un modèle local — quelques minutes pour un petit README, jusqu'à une heure environ pour un document volumineux découpé en sections.

Les langues disposant déjà d'un fichier `docs/<language>/README.md` ne sont pas retraduites intégralement : le réviseur compare la traduction existante avec la source actuelle et, seulement si des changements sont détectés, le rédacteur applique des modifications minimales. Les traductions à jour sont totalement ignorées, ainsi, relancer le pipeline après une modification du README ne traite que les parties obsolètes.

Une fois le travail par langue terminé, l'exécution s'achève en déplaçant (si nécessaire) le `README.md` source de la racine vers `docs/<source_language>/` et en régénérant le `README.md` racine comme une courte page de sélection liant chaque traduction non vide.

Nécessite que le serveur local de LM Studio soit actif (voir `config.json`) avec un modèle de chat chargé — le pipeline pilote le modèle via des complétions de texte brut et gère lui-même l'écriture des fichiers, donc le modèle **n'a pas** besoin de supporter les appels d'outils (tool calls) de style OpenAI (voir "Gestion des README volumineux" ci-dessous). Il est tout de même recommandé de tester une seule langue avant de lancer un traitement complet sur toute la liste.

### Gestion des README volumineux

Traduire un README volumineux (les documents frères `A-Starry-Sky` / `a-restless-ocean` font environ 35–60 Ko) en une seule complétion est le principal risque de fiabilité avec un modèle local : celui-ci peut manquer de jetons de sortie ou de contexte en cours de route, entraînant une troncature silencieuse de la fin du texte. Le mode `pipeline` est conçu pour éviter cela :

- **Conçu pour se passer d'outils.** Le modèle ne produit que du texte brut — chaque traduction, réécriture et page de répertoire revient sous forme de réponse, et l'orchestrateur l'enregistre lui-même via les outils `write_readme` / `write_directory_readme` du serveur. On ne demande jamais au modèle d'insérer un document entier dans l'argument d'un appel d'outil. Sur les modèles de *raisonnement* locaux (ex: Gemma 4), cette approche tronquerait le JSON de l'argument et le point de terminaison rejetterait la requête avec une erreur `peg-gemma4 format` / sortie malformée ; renvoyer du texte contourne entièrement ce problème.
- **`max_tokens`** (par défaut `32768`) est envoyé explicitement à chaque complétion afin qu'une section ou un brouillon complet puisse se terminer au lieu d'être coupé par la valeur par défaut plus courte de LM Studio. Le pipeline avertit si une complétion s'arrête tout de même pour cause de longueur (`length`), vous signalant qu'il faut augmenter ce seuil.
- **Découpage en sections** — lorsque la source dépasse `chunk_threshold_chars` (par défaut `12000`) et que `chunk_translation` est à `true`, la source est divisée selon les titres Markdown de premier niveau (`## `). Le système reconnaît les blocs de code (fences), donc un `##` à l'intérieur d'un bloc de code est ignoré. Chaque section est traduite dans sa propre complétion, puis l'orchestrateur assemble et enregistre les morceaux. Aucun appel au modèle n'a besoin de générer le document entier.
- **Révision par section** — avec `review_sections` à `true` (par défaut), chaque section suit la même boucle critique $\rightarrow$ révision que le mode simple, mais limitée à cette seule section : le réviseur compare la section traduite à sa source et le rédacteur révise jusqu'à ce que le réviseur soit d'accord (ou que `MAX_ITERATIONS` soit atteint). Comme une section est petite, la révision et la réécriture restent bien en dessous du plafond de troncature qui rendait la révision globale d'un gros README risquée.

Le flux découpé ne lance **pas** volontairement de seconde révision globale après coup — régénérer l'intégralité d'un grand README en une seule complétion réintroduirait le risque de troncature, et la passe par section a déjà couvert le travail. Réglez `review_sections` sur `false` pour traduire de gros documents sans aucune révision, ou `chunk_translation` sur `false` pour forcer le comportement initial en une seule passe (qui exécute toujours la boucle complète de révision globale). Le flux simple reste inchangé pour les documents sous le seuil.