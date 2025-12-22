# Chatter Copilot Backend

AI-powered assistant for OnlyFans chatters - get real-time recommendations based on proven techniques.

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the server
uvicorn src.main:app --reload

# Run tests
pytest
```

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - OpenAPI documentation
