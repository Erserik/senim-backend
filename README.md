# Senim Backend

Backend API for **Senim** — marketplace for home services in Almaty, Kazakhstan.

Built with FastAPI + SQLAlchemy (async) + SQLite (dev) / PostgreSQL (prod).

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## API Endpoints (36 total)

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/send-sms` | Send SMS verification code |
| POST | `/api/auth/verify-sms` | Verify code, get JWT token |
| POST | `/api/auth/profile` | Set name, city, photo |
| POST | `/api/auth/role` | Set role (client/master) |
| GET | `/api/auth/me` | Get current user |

### Master Onboarding
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/onboarding/specializations` | Set specializations |
| POST | `/api/onboarding/experience` | Set experience + bio |
| POST | `/api/onboarding/portfolio` | Set portfolio images |
| POST | `/api/onboarding/districts` | Set service districts |
| POST | `/api/onboarding/prices` | Set price ranges |
| POST | `/api/onboarding/complete` | Mark onboarding done |
| GET | `/api/onboarding/status` | Get onboarding progress |

### Orders
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/orders` | List active orders (for masters) |
| POST | `/api/orders` | Create order (client) |
| GET | `/api/orders/my` | My orders (client) |
| GET | `/api/orders/{id}` | Order details + responses |
| PATCH | `/api/orders/{id}/cancel` | Cancel order |

### Responses (Master Bids)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/responses/orders/{id}` | Respond to order |
| GET | `/api/responses/my` | My responses |
| PUT | `/api/responses/{id}` | Edit response |
| DELETE | `/api/responses/{id}` | Cancel response |
| POST | `/api/responses/{id}/accept` | Client accepts response |

### Chats
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/chats` | List my chats |
| GET | `/api/chats/{id}/messages` | Get messages |
| POST | `/api/chats/{id}/messages` | Send message |

### Profile
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/profile/me` | My master profile |
| GET | `/api/profile/{user_id}` | View master profile |
| GET | `/api/profile/top/masters` | Top rated masters |
| GET | `/api/profile/reviews/recent` | Recent reviews |

### Reviews
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/reviews` | Create review |

### Settings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | Get settings |
| PUT | `/api/settings/profile` | Update profile |
| DELETE | `/api/settings/account` | Delete account |

### Reference
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/categories` | List categories |
| GET | `/api/districts` | List districts |
| GET | `/api/health` | Health check |

## Tech Stack

- **FastAPI** — async web framework
- **SQLAlchemy 2.0** — async ORM
- **Alembic** — database migrations
- **Pydantic v2** — validation & serialization
- **python-jose** — JWT authentication
- **SQLite** (dev) / **PostgreSQL** (prod via asyncpg)

## Project Structure

```
app/
  api/          # Route handlers (auth, orders, chats, etc.)
  core/         # Config, database, security
  models/       # SQLAlchemy models
  schemas/      # Pydantic request/response schemas
  services/     # Business logic (seed data, etc.)
  main.py       # FastAPI app entry point
alembic/        # Database migrations
tests/          # Test suite
```
