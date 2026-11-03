# papy-playlists

Scripts des routines cloud Claude (claude.ai/code/routines) qui génèrent les playlists Spotify « Papy ».

## Dépôts

- GitLab (principal) : https://gitlab.com/AnselmeSDR/papy-playlists
- GitHub (miroir, cloné par la routine) : https://github.com/AnselmeSDR/papy-playlists
- `git push` envoie aux deux (deux URL de push sur `origin`). Dépôts publics : aucun secret ici.

## Structure

- `papy-weekly/` : routine « Spotify - papy-weekly-playlist » (`trig_01XACKcfYN6DYELjPvagh2hr`, lundi 04:00 UTC),
  100 titres de découverte. `rules.py` (quotas, garde-fous de genre), `reco.py` (recommandation),
  `validate.py` (bloque l'écriture Spotify sans `PASS`). Détails : `papy-weekly/README.md`.
- `.mcp.json` : démarre le serveur MCP Spotify en clonant `AnselmeSDR/mcp-claude-spotify` dans `/tmp`
  (identifiants `SPOTIFY_*` fournis par l'environnement cloud « Spotify »).
- `.claude/settings.json` : autorise `python3 papy-weekly/reco.py` et `validate.py` (mode auto du cloud).
- La consigne de la routine est stockée dans la routine elle-même, pas dans ce dépôt.

## Contraintes cloud (constatées le 2026-11-03)

- Ce dépôt doit être la **seule source** de la routine : avec deux sources, la session démarre dans le
  dossier parent et aucun `.mcp.json` n'est chargé.
- Le mode auto refuse d'exécuter du code téléchargé pendant la session (« Code from External ») :
  les scripts doivent être dans le dépôt cloné, pas récupérés au démarrage.
- Python 3 stdlib uniquement (aucun `pip install`).
- Spotify (app en mode développement) bloque recommandations (404), playlists d'autres
  utilisateurs (403) et genres d'artistes : la similarité vient de Deezer (`api.deezer.com`, sans clé),
  les titres sont retrouvés sur Spotify par ISRC.
- Toute écriture Spotify passe par les outils MCP de l'agent, jamais par les scripts.
