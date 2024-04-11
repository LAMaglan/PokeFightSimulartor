from pydantic import BaseModel
from fastapi import HTTPException
from typing import List, Dict
import random
import csv
from logging_config import get_logger
import httpx


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
