# papy-playlists

Scripts des routines cloud Claude (claude.ai/code/routines) qui génèrent les playlists Spotify « Papy ».

## Dépôts

- GitLab (principal) : https://gitlab.com/AnselmeSDR/papy-playlists
- GitHub (miroir, cloné par les routines) : https://github.com/AnselmeSDR/papy-playlists
- `git push` envoie aux deux (deux URL de push sur `origin`).

## Structure

- `papy-weekly/` : routine « Spotify - papy-weekly-playlist » (`trig_01XACKcfYN6DYELjPvagh2hr`, lundi 04:00 UTC),
  100 titres de découverte. `rules.py` (quotas, garde-fous de genre), `reco.py` (recommandation),
  `validate.py` (bloque l'écriture Spotify sans `PASS`). Détails : `papy-weekly/README.md`.
- La routine clone aussi `AnselmeSDR/mcp-claude-spotify` (serveur MCP Spotify via son `.mcp.json`).
  La consigne de la routine est stockée dans la routine elle-même, pas dans ce dépôt.

## Contraintes

- Python 3 stdlib uniquement (aucun `pip install` dans le cloud).
- Spotify (app en mode développement) bloque recommandations (404), playlists d'autres
  utilisateurs (403) et genres d'artistes : la similarité vient de Deezer (`api.deezer.com`, sans clé),
  les titres sont retrouvés sur Spotify par ISRC.
- Toute écriture Spotify passe par les outils MCP de l'agent, jamais par les scripts.
