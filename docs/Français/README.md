# comprehend-markdown

*Vous effleurez le parchemin et prononcez l'incantation. Quelques minutes ou une heure plus tard (selon l'épaisseur du grimoire), vous comprenez le Markdown dans n'importe quelle langue.*

Un serveur MCP qui traduit le `README.md` d'un projet dans d'autres langues, accompagné d'un pipeline autonome qui exécute une boucle de rédaction et de révision via un modèle local LM Studio.

La langue source et les langues cibles sont configurables — l'anglais n'est que la valeur par défaut. Réglez `source_language` pour traduire *depuis* le chinois, l'indonésien ou toute autre langue, et `target_languages` pour choisir les langues de destination (voir [Choisir les langues source et cible](#choisir-les-langues-source-et-cible)).

Pour tout projet cible, l'outil s'attend à trouver (et crée si nécessaire) la structure suivante :

```
<project-root>/docs/<source>/README.md  la source canonique (anglais par défaut)
<project-root>/docs/<lang>/README.md    les versions traduites, une par langue
<project-root>/README.md                page d'accueil de sélection de langue (générée)
```

Les projets qui n'ont pas encore été migrés — dont la source se trouve toujours à la racine — sont également pris en charge : le `README.md` racine est utilisé comme source et, à la fin de l'exécution du `pipeline`, il est déplacé vers `docs/<source>/` (ex: `docs/English/`) et remplacé par une courte page d'accueil générée qui lie toutes les traductions disponibles.

## Installation

Tout (création du venv, installation/synchronisation des dépendances) est géré par `run.sh` — il n'y a pas d'étape d'installation séparée. Il lit les paquets depuis `requirements.txt` et les réinstalle à chaque exécution ; ainsi, pour mettre à jour les dépendances, il suffit de relancer le script.

Si vous souhaitez utiliser un modèle LM Studio local autre que celui par défaut, modifiez les valeurs dans `config.json`.

### Choisir les langues source et cible

Deux clés de configuration dans `config.json` contrôlent la direction de la traduction :

- **`source_language`** — la langue dans laquelle votre `README.md` canonique est écrit, ainsi que le nom de son dossier `docs/<source_language>/`. Par défaut : `English`. Réglez-le sur `中文`, `Indonesia` ou toute autre langue pour traduire *depuis* celle-ci.
- **`target_languages`** — la liste des langues vers lesquelles le pipeline traduit. Toute entrée identique à `source_language` est automatiquement ignorée, il est donc sans danger de laisser la source dans la liste.

Par exemple, pour traduire un README chinois vers l'anglais et l'espagnol :

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Si `target_languages` est omis, le pipeline utilise sa liste intégrée de 18 langues.

La clé `api_key` n'est utile que si vous avez activé l'option "Require API Key" dans les paramètres du serveur Developer de LM Studio — sinon, laissez-la sur `"lm-studio"`, valeur que LM Studio ignore. Notez que cela ne s'applique qu'au mode `pipeline`, qui est la seule partie appelant directement le point de terminaison compatible OpenAI de LM Studio ; le mode `serve` ne communique jamais avec l'API de LM Studio car c'est LM Studio lui-même qui agit comme client MCP.

Le paramètre `max_tokens` peut être défini ici, bien que je ne sois pas certain que LM Studio le respecte scrupuleusement. Assurez-vous de régler cette valeur à au moins 24576 directement dans le modèle avant d'exécuter ce script.

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

- **tool** `write_readme(language, content)` — écrit le fichier `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — écrit le `README.md` racine (la page de sélection de langue)
- **resource** `docs://readme` — la source (`docs/<source_language>/README.md`, ou le `README.md` racine par défaut)
- **resource** `docs://readme/{language}` — la traduction existante, le cas échéant
- **resource** `docs://dir_readme` — le `README.md` racine
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — la boucle de traduction initiale
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — le flux de mise à jour : compare une traduction existante avec la source actuelle et applique des corrections minimales
- **prompt** `create_docs_language_directory` — génère la page racine de sélection de langue à partir de la liste des traductions disponibles

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

Le second argument dans `args` est fixé lors de la connexion — la configuration de LM Studio étant un JSON statique sans support d'invite interactive, il doit s'agir du chemin réel du projet à traduire, et non du chemin de ce dépôt (à moins que ce dernier ne soit le projet visé).