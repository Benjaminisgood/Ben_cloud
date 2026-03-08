# Bencred - Agent Guidelines

## Mission
Secure credential management for Ben_cloud ecosystem. Store API keys, passwords, OAuth tokens, and other sensitive data with encryption.

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
Bencred/
├── apps/api/
│   ├── src/bencred_api/
│   │   ├── core/        # Configuration
│   │   ├── db/          # Database session & base
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── repositories/# Data access layer
│   │   ├── services/    # Business logic & encryption
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
| POST | `/api/v1/credentials` | Create credential (returns ID) |
| GET | `/api/v1/credentials` | List credentials (paginated) |
| GET | `/api/v1/credentials/{id}` | Get credential (no secret) |
| GET | `/api/v1/credentials/{id}/secret` | Get credential with decrypted secret |
| PUT | `/api/v1/credentials/{id}` | Update credential |
| DELETE | `/api/v1/credentials/{id}` | Delete credential |
| POST | `/api/v1/credentials/{id}/rotate` | Rotate credential secret |

## Security

- **Encryption**: All secrets encrypted with Fernet (symmetric encryption)
- **Audit**: Track `created_at`, `updated_at`, `accessed_at`, `last_rotated`
- **Rotation**: Built-in rotation reminder system
- **Access Control**: Integrate with Ben_cloud SSO (Benbot)

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
pytest tests/test_credentials.py -v

# With coverage
pytest --cov=bencred_api --cov-report=html
```

## Integration with Ben_cloud

- **Port**: 9600
- **SSO**: Benbot handles authentication, passes user context
- **Registry**: Listed in `/Users/benserver/Desktop/Ben_cloud/PROJECT_STANDARDS/registry.yaml`

## Rules

1. **Never log secrets** - All logging must sanitize sensitive data
2. **Always use migrations** - No `create_all` in production
3. **Write operations return ID** - For audit trail
4. **Run tests before commit** - `make test` must pass
5. **Encrypt at rest** - All secrets encrypted before database storage

## Troubleshooting

### Database locked
```bash
rm data/bencred.db
make migrate
```

### Encryption key changed
If FERNET_KEY changes, old credentials cannot be decrypted. Backup before rotation.

### Migration failed
```bash
alembic downgrade -1
# Fix migration file
alembic upgrade head
```
