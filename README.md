# Bakground
Pokemon fight simulator using FastAPI.
<br>
Details and sprites retrieved from https://pokeapi.co/ 
<br>
Sprites for typesretrieved from https://github.com/msikma/pokesprite
<br>
Frontend with HTML/Jinja

Note: a fair amount of help from ChatGPT throughout

## Details of battle simulation

Pokemon base stats, and effort values for each stat are extracted from [pokeapi.co](pokeapi.co). 
<br>
The actual stats used in the battle simulation are calculated based on these data, chosen level and a random "individual value": 
<br> 
see `update_stats` method within the `Pokemon` class (utils.py) for full details.
<br>
In the actual battle simulation (see `battle_simlator()` in utils.py) the pokemon with the highest speed becomes the first attacker.  
<br>
In the case of equal speed, a random pokemon is chosen. After each round, the defender and attacker switch roles, until one of the 
<br>
pokemon loses (HP reaches 0). During the battle, the cumulative type advantages across types for the
<br>
attacker are assessed against all the types that the defender has. The type advantages are `data/types.csv` based on [here](https://pokemondb.net/type).
<br>
Ff an attacker has a type that has no effect on one of the types the defender has, then the calculated damage is 0.


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

`pokemon_details.html`
<br>
![pokemon_stats_example](https://github.com/LAMaglan/PokeFightSimulator/assets/29206211/599298a2-9b7d-4b0c-8210-9314c574997f)

`battle.html`
<br>
![battle_example](https://github.com/LAMaglan/PokeFightSimulator/assets/29206211/5c7d37b3-55f1-4a68-9d8a-0d6e80575074)

`types.html`
<br>
![types_example](https://github.com/LAMaglan/PokeFightSimulator/assets/29206211/f0e6a296-fe40-40e6-913e-c433d9b78002)
