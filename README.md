Poekmon fight simulator using FastAPI

To run, install poetry from [here](https://python-poetry.org/docs/)

activate poetry environment

```
poetry shell
```

install dependencies from pyproject.toml

```
poetry install
```

start the FastAPI:

```
uvicorn main:app --reload
```

On local PC, will run on http://127.0.0.1:8000

See swagger docs in `/docs`, e.g.
`http://127.0.0.1:8000/docs`