from fastapi import APIRouter, HTTPException
from fastapi import HTTPException
import httpx
from collections import defaultdict

router = APIRouter()

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



@router.get("/pokemon/{pokemon_name}/locations")
async def get_pokemon_locations(pokemon_name: str):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}/encounters"
    locations = await get_locations(url)
    return locations