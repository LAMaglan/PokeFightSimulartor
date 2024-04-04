from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import httpx
from logging_config import (
    get_logger,
)  # Adjust the import statement according to your project structure
from typing import List
import random

# __name__ will set logger name as the file name: 'main'
logger = get_logger(__name__)

app = FastAPI()

templates = Jinja2Templates(directory="templates")


# Define Pokemon class
class Pokemon(BaseModel):
    name: str
    level: int = 1
    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int

    # Removed IV as (class) attribute, as
    # 1) there is one IV for each stat and also
    # 2) it is random

    class Config:
        pass

    def stat_modifier(self, stat, IV):
        # TODO: final should be something like
        # (2 x BaseStat + IV + (EV/4)) x Level / 100
        return int(((2 * stat + IV) * self.level) / 100)

    def apply_stat_modifier(
        self,
        stats={"attack", "special_attack", "speed", "hp", "defense", "special_defense"},
    ):
        for stat in stats:
            # IV for each stat. It is random so not stored as class attribute
            IV = random.randint(0, 31)
            if hasattr(self, stat):
                setattr(self, stat, self.stat_modifier(getattr(self, stat), IV))


# Initialize list with all pokemon names
pokemon_names_list = []

# set to arbitrarily high number (FastAPI startup event handler does not accept direct paramaters)
POKEMON_LIMIT = 2000


# NOTE: "on_event" deprecated, but still works
# get list of all pokemon names from pokeapi
@app.on_event("startup")
async def on_startup():
    global pokemon_names_list
    url = f"https://pokeapi.co/api/v2/pokemon?limit={POKEMON_LIMIT}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        pokemon_names_list = [result["name"] for result in data["results"]]


def clean_stat_names(stats: dict) -> dict:
    """
    Pokeapi has "special-defense" and "special-attack".
    To avoid syntax errors with python, converting "-" to "_"
    """
    return {key.replace("-", "_"): value for key, value in stats.items()}


def revert_stat_names(stats: dict) -> dict:
    return {key.replace("_", "-"): value for key, value in stats.items()}


async def get_pokemon(pokemon_name: str):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            pokemon_data = response.json()
            stats = {
                stat["stat"]["name"]: stat["base_stat"]
                for stat in pokemon_data["stats"]
            }
            stats = clean_stat_names(stats)

            pokemon = Pokemon(name=pokemon_name, **stats)
            sprites = pokemon_data["sprites"]
            types = [t["type"]["name"] for t in pokemon_data["types"]]
            return pokemon, sprites, types
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Pokemon not found"
            )


def battle_simulator(pokemon1: Pokemon, pokemon2: Pokemon):

    pokemon1.apply_stat_modifier()
    pokemon2.apply_stat_modifier()

    if pokemon1.speed > pokemon2.speed:
        attacker = pokemon1
        defender = pokemon2
    else:
        attacker = pokemon2
        defender = pokemon1

    while pokemon1.hp > 0 and pokemon2.hp > 0:
        if attacker.attack > defender.defense:
            damage = attacker.attack - defender.defense
            defender.hp -= damage
        elif attacker.special_attack > defender.special_defense:
            damage = attacker.special_attack - defender.special_defense
            defender.hp -= damage
        attacker, defender = (
            defender,
            attacker,
        )  # Players switch roles for the next round

    if pokemon1.hp <= 0:
        return pokemon2.name
    else:
        return pokemon1.name


# Custom HTTPException handler for FastAPI
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP Exception occurred: {exc.detail}")
    return JSONResponse(content={"detail": exc.detail}, status_code=exc.status_code)


# Define routes
@app.get("/")
async def read_pokemon_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Endpoint to pass all names to HTML as JSON
@app.get("/pokemon_names", response_model=List[str])
async def get_pokemon_names():
    return pokemon_names_list


@app.get("/pokemon/{pokemon_name}")
async def read_pokemon(request: Request, pokemon_name: str):
    try:
        logger.info(f"Fetching data for {pokemon_name}.")

        pokemon, pokemon_sprites, pokemon_types = await get_pokemon(pokemon_name)

        pokemon_stats = vars(pokemon)
        del pokemon_stats["name"]
        pokemon_stats = revert_stat_names(pokemon_stats)

        response = templates.TemplateResponse(
            "pokemon_stats.html",
            {
                "request": request,
                "pokemon": {
                    "name": pokemon_name,
                    "sprites": pokemon_sprites,
                    "types": pokemon_types,
                },
                "pokemon_stats": pokemon_stats,
            },
        )
        logger.info(f"Data for {pokemon_name} successfully fetched and returned.")
        return response
    except HTTPException as exc:
        logger.error(f"Error fetching data for {pokemon_name}: {str(exc)}")
        raise


@app.get("/battle")
async def battle(
    request: Request,
    pokemon1_name: str,
    pokemon2_name: str,
    pokemon1_level: int = Query(...),
    pokemon2_level: int = Query(...),
):
    try:

        pokemon1, pokemon1_sprites, _ = await get_pokemon(pokemon1_name)
        pokemon2, pokemon2_sprites, _ = await get_pokemon(pokemon2_name)

        # passed on from index.html
        pokemon1.level = pokemon1_level
        pokemon2.level = pokemon2_level

        logger.info(f"Initiating battle between {pokemon1_name} and {pokemon2_name}")

        winner = battle_simulator(pokemon1, pokemon2)

        return templates.TemplateResponse(
            "battle.html",
            {
                "request": request,
                "pokemon1": {
                    "name": pokemon1_name,
                    "sprite": pokemon1_sprites["front_default"],
                },
                "pokemon2": {
                    "name": pokemon2_name,
                    "sprite": pokemon2_sprites["front_default"],
                },
                "winner": winner,
            },
        )
    except HTTPException as exc:
        logger.error(f"Error during battle: {str(exc)}")
        raise
