from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import httpx
from logging_config import (
    get_logger,
)  # Adjust the import statement according to your project structure
from typing import List

# __name__ will set logger name as the file name: 'main'
logger = get_logger(__name__)

app = FastAPI()

templates = Jinja2Templates(directory="templates")


# Define Pokemon class
class Pokemon(BaseModel):
    name: str


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
            sprites = pokemon_data["sprites"]
            types = [t["type"]["name"] for t in pokemon_data["types"]]
            return stats, sprites, types
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Pokemon not found"
            )


async def calculate_stats_total(stats: dict):
    return sum(stats.values())


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
        pokemon_stats, pokemon_sprites, pokemon_types = await get_pokemon(pokemon_name)
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
async def battle(request: Request, pokemon1_name: str, pokemon2_name: str):
    try:
        logger.info(f"Initiating battle between {pokemon1_name} and {pokemon2_name}.")
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

        return templates.TemplateResponse(
            "battle.html",
            {
                "request": request,
                "pokemon1": {
                    "name": pokemon1_name,
                    "sprite": pokemon1_sprites["front_default"],
                    "total_stats": pokemon1_total,
                },
                "pokemon2": {
                    "name": pokemon2_name,
                    "sprite": pokemon2_sprites["front_default"],
                    "total_stats": pokemon2_total,
                },
                "winner": winner,
            },
        )
    except HTTPException as exc:
        logger.error(f"Error during battle: {str(exc)}")
        raise
