from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
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


# Configure static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


# Define Pokemon class
class Pokemon(BaseModel):
    name: str
    level: int = 1

    # Stats directly taken from pokeAPI
    # TODO: later find out if can use type annotation
    # to get attribute with dict{base_stat: int, effort: int}
    hp: Dict[str, int]
    attack: Dict[str, int]
    defense: Dict[str, int]
    special_attack: Dict[str, int]
    special_defense: Dict[str, int]
    speed: Dict[str, int]
    types: List[str]

    # updated stats based on custom formula
    hp_updated: float = 0
    attack_updated: float = 0
    defense_updated: float = 0
    special_attack_updated: float = 0
    special_defense_updated: float = 0
    speed_updated: float = 0

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "FakeMon",
                    "level": 5,
                    "hp": {"base_stat": 10, "effort": 0},
                    "attack": {"base_stat": 30, "effort": 0},
                    "defense": {"base_stat": 35, "effort": 1},
                    "special_attack": {"base_stat": 25, "effort": 2},
                    "special_defense": {"base_stat": 10, "effort": 0},
                    "speed": {"base_stat": 10, "effort": 1},
                    "types": ["electric", "water"],
                    "hp_updated": 10,
                    "attack_updated": 15,
                    "defense_updated": 40,
                    "special_attack_updated": 30,
                    "special_defense_updated": 25,
                    "speed_updated": 20,
                }
            ]
        }
    }

    def update_stat(self, stat: Dict[str, int], base_modifier: int = 5) -> int:
        IV = random.randint(0, 31)
        base_stat = stat["base_stat"]
        effort = stat["effort"]
        updated_base_stat = int(
            ((2 * base_stat + IV + (effort / 4)) * (self.level / 100)) + base_modifier
        )
        return updated_base_stat

    def stats_modifier(self):
        # Higher "constant" (base_modifier) only for HP
        self.hp_updated = self.update_stat(self.hp, base_modifier=10)
        self.attack_updated = self.update_stat(self.attack)
        self.defense_updated = self.update_stat(self.defense)
        self.special_attack_updated = self.update_stat(self.special_attack)
        self.special_defense_updated = self.update_stat(self.special_defense)
        self.speed_updated = self.update_stat(self.speed)


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
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # Check if both 'results' and 'name' keys exist in the response,
            # required to generate `pokemon_names_list`
            if "results" not in data and "name" not in data.get("results", [{}])[0]:
                raise KeyError(
                    "Both 'results' and 'name' keys not found in data fetched from pokeapi."
                )
            elif "results" not in data:
                raise KeyError(
                    "'results' key not found in response data fetched from pokeapi."
                )
            elif "name" not in data.get("results", [{}])[0]:
                raise KeyError(
                    "'name' key not found in response data fetched from pokeapi."
                )

            pokemon_names_list = [result["name"] for result in data["results"]]

    except httpx.RequestError as exc:
        # Request failed or connection error
        logger.error(
            f"Request failed or connection error required for getting pokemon names: {str(exc)}"
        )

    except httpx.HTTPError as exc:
        logger.error(f"Invalid url, response or failed JSON serialization: {str(exc)}")


@app.on_event("startup")
async def on_startup_types():
    await parse_types_csv()


async def parse_types_csv():
    global type_advantages
    filepath = "data/types.csv"
    try:
        with open(filepath, "r") as file:
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
    except FileNotFoundError as exc:
        logger.error(f"Error reading data in {filepath}: {str(exc)}")
        raise


def clean_stat_names(stats: dict) -> dict:
    """
    Pokeapi has "special-defense" and "special-attack".
    To avoid syntax errors with python, converting "-" to "_"
    """
    return {key.replace("-", "_"): value for key, value in stats.items()}


def revert_stat_names(stats: dict) -> dict:
    return {key.replace("_", "-"): value for key, value in stats.items()}


def calculate_damage(level, attack_power, defense_power):
    """
    Calculate damage based on the Pokémon's level, attack power, and defense power.
    This is a simplified example and may need to be customized for your specific needs.
    """
    # Placeholder for any modifiers to damage (e.g., critical hits, randomization)
    modifier = 1

    # Basic damage calculation
    damage = (
        ((2 * level) / 5 + 2) * attack_power * (attack_power / defense_power) / 50 + 2
    ) * modifier

    return damage


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
            # TODO: now with the stat_updated attributes, get error here:
            # "hp_updated Field required [type=missing, input_value={'name': 'ivysaur', 'hp':...s': ['grass', 'poison']}, input_type=dict]"

            pokemon = Pokemon(name=pokemon_name, **stats, types=types)
            sprites = pokemon_data["sprites"]

            return pokemon, sprites
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Pokemon not found"
            )


def battle_simulator(pokemon1: Pokemon, pokemon2: Pokemon, type_advantages: dict):

    pokemon1.stats_modifier()
    pokemon2.stats_modifier()

    while pokemon1.hp_updated > 0 and pokemon2.hp_updated > 0:
        attacker, defender = (
            (pokemon1, pokemon2)
            if pokemon1.speed_updated > pokemon2.speed_updated
            else (pokemon2, pokemon1)
        )

        # loop over types of the attacker, but collective used
        for _ in attacker.types:

            # For now, take average of "physical" and "special" stats
            attack_power = (
                attacker.attack_updated + attacker.special_attack_updated
            ) / 2
            defense_power = (
                defender.defense_updated + defender.special_defense_updated
            ) / 2

            damage = calculate_damage(attacker.level, attack_power, defense_power)

            type_effectiveness = 1

            for defending_type in defender.types:

                effectiveness = 1
                for attack_type in attacker.types:

                    # attacker effectiveness of each type across defender types
                    effectiveness *= type_advantages.get(attack_type, {}).get(
                        defending_type, 1
                    )

                # Collect cumulative type effectiveness of attacker
                type_effectiveness *= effectiveness

            # Apply type effectiveness to the damage
            damage *= type_effectiveness
            defender.hp_updated -= damage

            pokemon1, pokemon2 = defender, attacker

    return defender.name if pokemon2.hp_updated <= 0 else attacker.name


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


# endpoint that links to HTML displaying type advantages
@app.get("/types")
async def display_type_advantages(request: Request):
    defending_types = list(type_advantages[next(iter(type_advantages))].keys())
    return templates.TemplateResponse(
        "types.html",
        {
            "request": request,
            "type_advantages": type_advantages,
            "defending_types": defending_types,
        },
    )


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

        # Collect the {stat}_updated attributes to delete
        attrs_to_delete = [
            stat for stat in pokemon_stats.keys() if stat.endswith("_updated")
        ]

        # Delete the {stat}_updated attributes
        for attr in attrs_to_delete:
            del pokemon_stats[attr]

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
