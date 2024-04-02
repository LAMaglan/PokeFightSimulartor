# Bakground
Pokemon fight simulator using FastAPI.
<br>
Details and sprites retrieved from https://pokeapi.co/ 
<br>
Sprites for typesretrieved from https://github.com/msikma/pokesprite
<br>
Frontend with HTML/Jinja

# General

Can run with poetry locally, or with docker

## Container (docker)

To run with docker, install docker from [here](https://docs.docker.com/engine/install/)

Build the docker image

```
docker build -t <chosen image name>
```

Run the docker container


```docker
docker run -d -p 8000:80 <name from previous step>
```


On local PC, will run on http://127.0.0.1:8000 (open in a browser)

See swagger docs in `/docs`, e.g.
`http://127.0.0.1:8000/docs`

To stop the docker container, run
```docker
docker stop <name of container, can get from `docker ps`>
```

Alternatively, can run without the `-d` flag
```docker
docker run -p 8000:80 <name from previous step>
```
<br>
The docker container will be "removed" when terminal/process is shut
(i.e. no need to manually stop).
<br>
This latter approach is more useful for logging purposes,
<br>
unless logging is written to file (see logging_config.py)

## Poetry (local)

To run with poetry, install poetry from [here](https://python-poetry.org/docs/)

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
