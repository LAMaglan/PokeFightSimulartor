from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

# Define Pokemon class
class Pokemon(BaseModel):
    name: str

async def get_pokemon_stats(pokemon_name: str):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            pokemon_data = response.json()
            # Extract the stats
            stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon_data["stats"]}
            return stats
        else:
            raise HTTPException(status_code=response.status_code, detail="Pokemon not found")

async def calculate_stats_total(stats: dict):
    return sum(stats.values())

# Define routes
@app.get("/pokemon/{pokemon_name}")
async def read_pokemon(pokemon_name: str):
    pokemon_stats = await get_pokemon_stats(pokemon_name)
    return {"pokemon_stats": pokemon_stats}


@app.get("/battle/{pokemon1_name}/{pokemon2_name}")
async def battle(pokemon1_name: str, pokemon2_name: str):
    pokemon1_stats = await get_pokemon_stats(pokemon1_name)
    pokemon2_stats = await get_pokemon_stats(pokemon2_name)

    pokemon1_total = await calculate_stats_total(pokemon1_stats)
    pokemon2_total = await calculate_stats_total(pokemon2_stats)

    if pokemon1_total > pokemon2_total:
        winner = pokemon1_name
    elif pokemon1_total < pokemon2_total:
        winner = pokemon2_name
    else:
        winner = "It's a tie!"

    return {
        "battle_result": {
            "winner": winner,
            "pokemon1_total_stats": pokemon1_total,
            "pokemon2_total_stats": pokemon2_total,
        }
    }