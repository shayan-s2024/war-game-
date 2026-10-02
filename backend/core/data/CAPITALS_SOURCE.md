# Capital name data

`country_capitals.json` assigns a capital or designated seat to every playable entry in `core/gamedata.py` (450 entries). Sovereign-country names and available territories use the `mledoze/countries` dataset (Persian country labels and listed capital names); game-only islands and fictional realms use an explicit local seat. Any additional catalog entry has a readable central-seat fallback in `core.services.country_geo.capital_for_country`.

Reference dataset: https://github.com/mledoze/countries (countries.json). The 3D “My Country” redesign source is the user-provided `3d-war-game-redesign.zip`.
