from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx
from logging_config import get_logger
from typing import List
from utils import (
    type_advantages,
    parse_types_csv,
    extract_pokemon_base_stats,
    get_pokemon,
    battle_simulator,
)

# __name__ will set logger name as the file name: 'main'
logger = get_logger(__name__)

app = FastAPI()

templates = Jinja2Templates(directory="templates")


# Configure static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


# Initialize list with all pokemon names
pokemon_names_list = []

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

        pokemon, pokemon_sprites, cry, weight, height = await get_pokemon(pokemon_name)
        pokemon_types = pokemon.types
        pokemon_stats = extract_pokemon_base_stats(pokemon)

        response = templates.TemplateResponse(
            "pokemon_details.html",
            {
                "request": request,
                "pokemon": {
                    "name": pokemon_name,
                    "sprites": pokemon_sprites,
                    "types": pokemon_types,
                },
                "pokemon_stats": pokemon_stats,
                "cry": cry,
                "weight": weight,
                "height": height
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
            _, _, _
        ) = await get_pokemon(pokemon1_name)
        (
            pokemon2,
            pokemon2_sprites,
            _, _, _
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
