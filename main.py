from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

# Define Pokemon class
class Pokemon(BaseModel):
    name: str

async def get_pokemon(pokemon_name: str):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail="Pokemon not found")

# Define routes
@app.get("/pokemon/{pokemon_name}")
async def read_pokemon(pokemon_name: str):
    pokemon_data = await get_pokemon(pokemon_name)
    return {"pokemon_data": pokemon_data}


@app.post("/fight/")
def create_fight(pokemon1: Pokemon, pokemon2: Pokemon):
    # Mock fighting logic
    if "a" in pokemon1.name:
        winner = pokemon1.name
    else:
        winner = pokemon2.name
    return {"winner": winner}