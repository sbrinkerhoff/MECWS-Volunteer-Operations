FROM python:3.10-slim

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency definitions
COPY pyproject.toml uv.lock ./

# Generate requirements and install into system python
# We use --system to avoid creating a virtualenv inside the container
RUN uv export --format requirements-txt --no-dev --locked > requirements.txt && \
    uv pip install --system -r requirements.txt && \
    rm requirements.txt

# Copy the rest of the application
# (Note: This is technically redundant if docker-compose mounts the volume, 
# but good practice for building the image standalone)
COPY . .

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]
