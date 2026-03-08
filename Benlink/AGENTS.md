# Benlink - Agent Guidelines

## Mission
Link collection and management for Ben_cloud ecosystem. Save, organize, and track interesting links encountered during internet browsing.

## Quick Start

```bash
# Install dependencies
cd apps/api && make install

# Run migrations
make migrate

# Start development server
make dev

# Run tests
make test
```

## Architecture

```
Benlink/
├── apps/api/
│   ├── src/benlink_api/
│   │   ├── core/        # Configuration
│   │   ├── db/          # Database session & base
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── repositories/# Data access layer
│   │   ├── services/    # Business logic & metadata fetching
│   │   ├── api/         # FastAPI routers
│   │   └── main.py      # App entry point
│   ├── alembic/         # Database migrations
│   ├── tests/           # Pytest tests
│   └── Makefile
├── data/                # SQLite database
└── logs/                # Application logs
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/links` | Create link (auto-fetch metadata) |
| GET | `/api/v1/links` | List links (paginated, filterable) |
| GET | `/api/v1/links/{id}` | Get link by ID |
| PUT | `/api/v1/links/{id}` | Update link |
| DELETE | `/api/v1/links/{id}` | Delete link |
| POST | `/api/v1/links/{id}/refresh` | Refresh metadata from URL |
| POST | `/api/v1/links/{id}/favorite` | Mark as favorite |
| POST | `/api/v1/links/{id}/status` | Update reading status |

## Features

- **Auto Metadata Fetch**: Automatically extracts title, description, og_image from URLs
- **Reading Status**: Track unread → reading → read → archived
- **Priority System**: low, normal, high, urgent
- **Favorites**: Mark important links
- **Tagging**: Organize with custom tags
- **Categories**: reading, reference, tool, inspiration, etc.

## Database

Uses SQLite for development. Production should use PostgreSQL.

```bash
# Create new migration
make migrate-gen m="add_new_field"

# Apply migrations
make migrate

# Rollback
make migrate-down
```

## Testing

```bash
# Run all tests
make test

# Run specific test
pytest tests/test_links.py -v

# With coverage
pytest --cov=benlink_api --cov-report=html
```

## Integration with Ben_cloud

- **Port**: 9700
- **SSO**: Benbot handles authentication, passes user context
- **Registry**: Listed in `/Users/benserver/Desktop/Ben_cloud/PROJECT_STANDARDS/registry.yaml`

## Rules

1. **Always use migrations** - No `create_all` in production
2. **Write operations return ID** - For audit trail
3. **Run tests before commit** - `make test` must pass
4. **Respect rate limits** - Metadata fetching has timeout (10s default)
5. **Unique URLs** - Prevent duplicate links

## Troubleshooting

### Database locked
```bash
rm data/benlink.db
make migrate
```

### Metadata fetch timeout
Increase `FETCH_TIMEOUT` in config or check network connectivity.

### Migration failed
```bash
alembic downgrade -1
# Fix migration file
alembic upgrade head
```

## Example Usage

```bash
# Add a link (auto-fetches metadata)
curl -X POST http://localhost:9700/api/v1/links \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "category": "reading", "tags": ["tech", "ai"]}'

# List unread links
curl http://localhost:9700/api/v1/links?status=unread

# Mark as read
curl -X POST "http://localhost:9700/api/v1/links/1/status?status=read"

# Add to favorites
curl -X POST "http://localhost:9700/api/v1/links/1/favorite?is_favorite=true"
```
