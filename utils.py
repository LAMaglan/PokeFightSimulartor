from pydantic import BaseModel
from fastapi import HTTPException
from typing import List, Dict, Tuple
import random
import csv
from logging_config import get_logger
import httpx
from collections import defaultdict

# __name__ will set logger name as the file name: 'utils'
logger = get_logger(__name__)

type_advantages = {}


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


def extract_pokemon_base_stats(pokemon: Pokemon) -> dict:
    pokemon_stats = vars(pokemon)
    del pokemon_stats["name"]
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
    return pokemon_stats

def get_preferred_cry(cries):
    if 'latest' in cries and cries['latest']:
        return cries['latest']
    elif 'legacy' in cries and cries['legacy']:
        return cries['legacy']
    else:
        return None

def get_generations(generations: dict) -> list:
    """
    In pokeapi, stored as : generation-i, generation-ii, etc.
    """
    generations =  [key for key in generations.keys() if key.startswith("generation")]
    return [gen.replace('generation-', '') for gen in generations]

async def fetch_json(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Resource not found at URL: " + url
            )

async def get_locations(location_encounter_url: str) -> defaultdict:
    """
    Returns a nested dictionary organized by region, with each region mapping to a list
    of unique area names within that region.

    Assumes the provided URL yields a JSON response in a specific structure,
    with relevant data at 'location_area' -> 'location' -> 'region'.
    """
    nested_locations = defaultdict(list)

    # Fetch the list of location areas encounters
    location_area_urls = [location["location_area"]["url"] for location in await fetch_json(location_encounter_url)]

    # Iterate through each location area URL to fetch the area and region
    for location_area_url in location_area_urls:
        location_area_json = await fetch_json(location_area_url)
        location_json = await fetch_json(location_area_json["location"]["url"])
        
        area = location_area_json["location"]["name"]
        region = location_json["region"]["name"]
        nested_locations[region].append(area)

    # Deduplicate the areas within each region
    for region in nested_locations:
        nested_locations[region] = list(set(nested_locations[region]))

    return nested_locations

        


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
            cry = get_preferred_cry(pokemon_data["cries"])
            weight = pokemon_data["weight"] / 10 #kg
            height = pokemon_data["height"] / 10 #m
            generations = get_generations(pokemon_data["sprites"]["versions"])
            locations = await get_locations(pokemon_data["location_area_encounters"])

            return pokemon, sprites, cry, weight, height, generations, locations
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Pokemon not found"
            )


def determine_attacker(pokemon1: Pokemon, pokemon2: Pokemon) -> Tuple[Pokemon, Pokemon]:
    if pokemon1.speed_updated == pokemon2.speed_updated:
        attacker = random.choice([pokemon1, pokemon2])
        defender = pokemon2 if attacker == pokemon1 else pokemon1
    else:
        attacker, defender = (
            (pokemon1, pokemon2) if pokemon1.speed_updated > pokemon2.speed_updated else (pokemon2, pokemon1)
        )
    return attacker, defender

def sanity_check_attacker(turn: int, prev_attacker_name: str, current_attacker_name: str):
    if prev_attacker_name is current_attacker_name == prev_attacker_name and turn != 1:
        raise ValueError(f"Attacker {current_attacker_name} is the same in consecutive rounds!")

def calculate_round_damage(attacker: Pokemon, defender: Pokemon, type_advantages: dict) -> float:
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
        return damage

def perform_attack(attacker: Pokemon, defender: Pokemon, type_advantages: dict):
    # assuming one iteration is meant for the loop
    damage = calculate_round_damage(attacker, defender, type_advantages)
    defender.hp_updated -= damage

def battle_loop(pokemon1: Pokemon, pokemon2: Pokemon, type_advantages: dict) -> str:
    attacker, defender = determine_attacker(pokemon1, pokemon2)
    turn = 0
    prev_attacker_name = attacker.name

    while attacker.hp_updated > 0 and defender.hp_updated > 0:
        turn += 1
        sanity_check_attacker(turn, prev_attacker_name, attacker.name)
        prev_attacker_name = attacker.name

        logger.info(
            f"Battle simulator --- This is round {turn}. The attacker is {attacker.name} \
            and the defender is {defender.name}. The defender has HP {defender.hp_updated}"
        )

        perform_attack(attacker, defender, type_advantages)

        attacker, defender = defender, attacker

    return defender.name if attacker.hp_updated <= 0 else attacker.name

def battle_simulator(pokemon1: Pokemon, pokemon2: Pokemon, type_advantages: dict):
    pokemon1.stats_modifier()
    pokemon2.stats_modifier()

    logger.info(
        f"Battle simulator --- pokemon1: {pokemon1.name} has speed {pokemon1.speed_updated}"
    )
    logger.info(
        f"Battle simulator --- pokemon2: {pokemon2.name} has speed {pokemon2.speed_updated}"
    )

    return battle_loop(pokemon1, pokemon2, type_advantages)