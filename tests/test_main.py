import pytest
import responses
import random
from httpx import AsyncClient
from main import app

def generate_random_stats():
    return [
        {"base_stat": random.randint(1, 250), "stat": {"name": "hp"}},
        
        # TODO: figure out more plausible values later
        {"base_stat": random.randint(20, 100), "stat": {"name": "attack"}},
        {"base_stat": random.randint(20, 100), "stat": {"name": "defense"}},
        {"base_stat": random.randint(20, 100), "stat": {"name": "special-attack"}},
        {"base_stat": random.randint(20, 100), "stat": {"name": "special-defense"}},
        {"base_stat": random.randint(20, 150), "stat": {"name": "speed"}}
    ]

def generate_random_sprites():
    return {
        "front_default": f"https://example.com/sprite{random.randint(1, 100)}.png",
    }

def generate_random_types():
    types = ["electric", "fire", "water", "grass"]
    return [{"type": {"name": random.choice(types)}}]

# TODO: for some reason, returns as HTML rather than JSON
@pytest.fixture
def mock_pokemon_api():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            responses.GET,
            "https://pokeapi.co/api/v2/pokemon/pikachu",
            json={
                "stats": generate_random_stats(),
                "sprites": generate_random_sprites(),
                "types": generate_random_types(),
            },
            status=200,
        )
        yield rsps

@pytest.mark.asyncio
async def test_read_pokemon(mock_pokemon_api):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/pokemon/pikachu")
    assert response.status_code == 200
    # Parse the response as JSON.
    response_json = response.json()
    # Perform JSON structure-based assertions.
    assert "sprites" in response_json
    assert "types" in response_json
    assert "stats" in response_json
    assert all(stat["base_stat"] for stat in response_json["stats"])