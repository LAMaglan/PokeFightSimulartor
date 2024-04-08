from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import httpx
from logging_config import (
    get_logger,
)  # Adjust the import statement according to your project structure
from typing import List, Dict
import random
import csv

# __name__ will set logger name as the file name: 'main'
logger = get_logger(__name__)

app = FastAPI()

templates = Jinja2Templates(directory="templates")


# Define Pokemon class
class Pokemon(BaseModel):
    name: str
    level: int = 1

    # TODO: later find out if can use type annotation
    # to get attribute with dict{base_stat: int, effort: int}

    hp: Dict[str, int]
    attack: Dict[str, int]
    defense: Dict[str, int]
    special_attack: Dict[str, int]
    special_defense: Dict[str, int]
    speed: Dict[str, int]
    types: List[str]

    # TODO: consider having new attributes, that
    # will have stored after apply_stat_modifier
    # e.g. hp_actual, defense_actual, etc.

    # Removed IV as (class) attribute, as
    # 1) there is one IV for each stat and also
    # 2) it is random

    class Config:
        pass

    def update_stat(self, stat: Dict[str, int]):
        IV = random.randint(0, 31)
        stat["base_stat"] = int(
            (2 * stat["base_stat"] + IV + (stat["effort"] / 4)) * (self.level / 100)
        )

    def stats_modifier(self):
        self.update_stat(self.hp)
        self.update_stat(self.attack)
        self.update_stat(self.defense)
        self.update_stat(self.special_attack)
        self.update_stat(self.special_defense)
        self.update_stat(self.speed)


# Initialize list with all pokemon names
pokemon_names_list = []
type_advantages = {}

# set to arbitrarily high number (FastAPI startup event handler does not accept direct paramaters)
POKEMON_LIMIT = 2000


# NOTE: "on_event" deprecated, but still works
# get list of all pokemon names from pokeapi
@app.on_event("startup")
async def on_startup_names():
    global pokemon_names_list
    url = f"https://pokeapi.co/api/v2/pokemon?limit={POKEMON_LIMIT}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        pokemon_names_list = [result["name"] for result in data["results"]]


@app.on_event("startup")
async def on_startup_types():
    await parse_types_csv()


async def parse_types_csv():
    global type_advantages
    with open("data/types.csv", "r") as file:
        csv_reader = csv.reader(file)
        headers = next(csv_reader)
        for row in csv_reader:

            # Lower case to match with pokeapi
            row_dict = {
                header.lower(): float(value)
                for header, value in zip(headers[1:], row[1:])
            }
            # Convert keys within the dictionary to lowercase
            lowercase_key_row_dict = {k.lower(): v for k, v in row_dict.items()}
            type_advantages[row[0].lower()] = lowercase_key_row_dict


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
                stat["stat"]["name"]: {
                    "base_stat": stat["base_stat"],
                    "effort": stat["effort"],
                }
                for stat in pokemon_data["stats"]
            }

            stats = clean_stat_names(stats)
            types = [t["type"]["name"] for t in pokemon_data["types"]]
            pokemon = Pokemon(name=pokemon_name, **stats, types=types)
            sprites = pokemon_data["sprites"]

            return pokemon, sprites
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Pokemon not found"
            )


def battle_simulator(pokemon1: Pokemon, pokemon2: Pokemon, type_advantages: dict):

    # TEST
    print(pokemon1.hp)
    print(pokemon2.hp)
    print("--------------")

    pokemon1.stats_modifier()
    pokemon2.stats_modifier()

    # TEST
    print(pokemon1.hp)
    print(pokemon2.hp)
    print("--------------")

    while pokemon1.hp["base_stat"] > 0 and pokemon2.hp["base_stat"] > 0:
        attacker, defender = (
            (pokemon1, pokemon2)
            if pokemon1.speed["base_stat"] > pokemon2.speed["base_stat"]
            else (pokemon2, pokemon1)
        )

        for atk_type in attacker.types:
            attack_power = (
                attacker.attack["base_stat"] + attacker.special_attack["base_stat"]
            ) / 2
            defense_power = (
                defender.defense["base_stat"] + defender.special_defense["base_stat"]
            ) / 2
            damage = max(1, int((attack_power - defense_power) / 2))

            type_effectiveness = 1
            for defending_type in defender.types:
                type_effectiveness *= type_advantages.get(atk_type, {}).get(
                    defending_type, 1
                )

            # TEST
            print(damage)
            #
            damage *= type_effectiveness
            # TEST
            print(damage)
            #
            defender.hp["base_stat"] -= damage

        pokemon1, pokemon2 = defender, attacker

    return attacker.name if pokemon2.hp["base_stat"] <= 0 else defender.name


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


# endpoint that shows type advantages as nested dict
@app.get("/type-advantages")
async def get_type_advantages():
    return type_advantages


@app.get("/pokemon/{pokemon_name}")
async def read_pokemon(request: Request, pokemon_name: str):
    try:
        logger.info(f"Fetching data for {pokemon_name}.")

        pokemon, pokemon_sprites = await get_pokemon(pokemon_name)

        pokemon_stats = vars(pokemon)
        del pokemon_stats["name"]
        pokemon_types = pokemon.types
        del pokemon_stats["types"]
        del pokemon_stats["level"]
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
        (
            pokemon1,
            pokemon1_sprites,
        ) = await get_pokemon(pokemon1_name)
        (
            pokemon2,
            pokemon2_sprites,
        ) = await get_pokemon(pokemon2_name)

        # passed on from index.html
        pokemon1.level = pokemon1_level
        pokemon2.level = pokemon2_level

        logger.info(
            f"Initiating battle between {pokemon1_name} at level {pokemon1_level} and {pokemon2_name} at level {pokemon2_level}"
        )

        winner = battle_simulator(pokemon1, pokemon2, type_advantages)

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
