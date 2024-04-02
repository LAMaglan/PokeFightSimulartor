# Bakground
Pokemon fight simulator using FastAPI.
<br>
Details etrieved from https://pokeapi.co/ 
<br>
Sprites retrieved from https://github.com/msikma/pokesprite (explicit for types)
<br>
Frontend with HTML/Jinja

# General

To run, install poetry from [here](https://python-poetry.org/docs/)

activate poetry environment

```
poetry shell
```

install dependencies from pyproject.toml

```
poetry install
```

start the FastAPI:

```
uvicorn main:app --reload
```

On local PC, will run on http://127.0.0.1:8000

See swagger docs in `/docs`, e.g.
`http://127.0.0.1:8000/docs`

# Example images

`index.html`
<br>
![index_example](https://github.com/LAMaglan/PokeFightSimulator/assets/29206211/564d3eb0-d0b6-42c4-b875-01fca96c518d)

`pokemon_stats.html`
<br>
![pokemon_stats_example](https://github.com/LAMaglan/PokeFightSimulator/assets/29206211/599298a2-9b7d-4b0c-8210-9314c574997f)

`battle.html`
<br>
![battle_example](https://github.com/LAMaglan/PokeFightSimulator/assets/29206211/5c7d37b3-55f1-4a68-9d8a-0d6e80575074)
