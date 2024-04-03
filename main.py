from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import httpx
from config.logging_decorator import log_decorator  

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Define Pokemon class
class Pokemon(BaseModel):
    name: str

async def get_pokemon(pokemon_name: str):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            pokemon_data = response.json()
            stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon_data["stats"]}
            sprites = pokemon_data["sprites"]
            types = [t["type"]["name"] for t in pokemon_data["types"]]  
            return stats, sprites, types
        else:
            raise HTTPException(status_code=response.status_code, detail="Pokemon not found")


async def calculate_stats_total(stats: dict):
    return sum(stats.values())


# Custom HTTPException handler for FastAPI
@app.exception_handler(HTTPException)
@log_decorator(__name__)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(content={"detail": exc.detail}, status_code=exc.status_code)

# Define routes
@app.get("/")
async def read_pokemon_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@log_decorator(__name__)
@app.get("/pokemon/{pokemon_name}")
async def read_pokemon(request: Request, pokemon_name: str):
    pokemon_stats, pokemon_sprites, pokemon_types = await get_pokemon(pokemon_name)
    response = templates.TemplateResponse("pokemon_stats.html", {
        "request": request,
        "pokemon": {
            "name": pokemon_name,
            "sprites": pokemon_sprites,
            "types": pokemon_types
        },
        "pokemon_stats": pokemon_stats
    })
    return response


@log_decorator(__name__)
@app.get("/battle")
async def battle(request: Request, pokemon1_name: str, pokemon2_name: str):
    pokemon1_stats, pokemon1_sprites, _ = await get_pokemon(pokemon1_name)
    pokemon2_stats, pokemon2_sprites, _ = await get_pokemon(pokemon2_name)

    pokemon1_total = await calculate_stats_total(pokemon1_stats)
    pokemon2_total = await calculate_stats_total(pokemon2_stats)

    if pokemon1_total > pokemon2_total:
        winner = pokemon1_name
    elif pokemon1_total < pokemon2_total:
        winner = pokemon2_name
    else:
        winner = "It's a tie!"

    return templates.TemplateResponse("battle.html", {
        "request": request,
        "pokemon1": {
            "name": pokemon1_name,
            "sprite": pokemon1_sprites['front_default'],
            "total_stats": pokemon1_total  
        },
        "pokemon2": {
            "name": pokemon2_name,
            "sprite": pokemon2_sprites['front_default'],
            "total_stats": pokemon2_total  
        },
        "winner": winner
    })