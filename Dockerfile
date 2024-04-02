# Start with a Python base image
FROM python:3.11-slim

# prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1

# optimize any "printing"
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Copy the pyproject.toml and poetry.lock (if available) into the working directory
COPY pyproject.toml poetry.lock* /app/

# Install Poetry
RUN pip install poetry

# Make sure poetry installs the packages into the system (not in a virtual environment)
RUN poetry config virtualenvs.create false

# Install the dependencies
# Use --no-dev if you don't want the dev dependencies
RUN poetry install --no-dev  


# Copy the rest of your application's code into the working directory
COPY . /app

# Command to run Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]