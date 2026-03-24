# Book Intelligence Agent

A living knowledge library — give it book titles, and it builds structured summaries, categorised by theme, with cross-book synthesis, conflicting views surfaced, and its own commentary on what matters most. Every new book enriches the whole.

## Architecture

- **FastAPI** — REST API with auto-generated OpenAPI docs
- **Claude API** (Anthropic) — The knowledge curator brain
- **PostgreSQL** — Persistent storage for the living library
- **Railway** — Deployment platform

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/books` | Process a single book → full Book Card |
| `POST` | `/books/batch` | Process 2–20 books → Book Cards + Batch Synthesis |
| `POST` | `/books/quick-add` | Quick-add a book without Claude processing |
| `POST` | `/master-log` | Generate/update the Master Log |
| `GET`  | `/master-log` | Get the latest Master Log |
| `POST` | `/query` | Query the library with any question |
| `GET`  | `/library` | Library stats overview |
| `GET`  | `/books` | List all books (filter by category, sort) |
| `GET`  | `/books/{id}` | Get a specific Book Card |
| `DELETE`| `/books/{id}` | Remove a book |
| `GET`  | `/categories` | List all categories with insights |
| `GET`  | `/themes` | List cross-book themes |
| `GET`  | `/debates` | List intellectual debates & tensions |
| `GET`  | `/ideas?q=search` | Search the idea index |

## Deploy to Railway

### 1. Push to GitHub

```bash
cd book-intelligence-agent
git init
git add .
git commit -m "Initial commit — Book Intelligence Agent"
git remote add origin https://github.com/YOUR_USERNAME/book-intelligence-agent.git
git push -u origin main
```

### 2. Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `book-intelligence-agent` repository

### 3. Add PostgreSQL

1. In your Railway project, click **+ New** → **Database** → **PostgreSQL**
2. Railway automatically sets the `DATABASE_URL` environment variable

### 4. Set Environment Variables

In your Railway service settings → **Variables**, add:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

That's it — `DATABASE_URL` is set automatically by Railway's PostgreSQL addon.

### 5. Deploy

Railway auto-deploys on push. Your API will be live at the URL Railway provides.

Visit `https://your-app.railway.app/docs` for the interactive Swagger UI.

## Usage Examples

### Add a single book
```bash
curl -X POST https://your-app.railway.app/books \
  -H "Content-Type: application/json" \
  -d '{
    "book_title": "Deep Work by Cal Newport",
    "depth": "FULL",
    "user_context": "Engineering manager protecting team focus time"
  }'
```

### Add a batch
```bash
curl -X POST https://your-app.railway.app/books/batch \
  -H "Content-Type: application/json" \
  -d '{
    "book_titles": [
      "Thinking, Fast and Slow by Daniel Kahneman",
      "Atomic Habits by James Clear",
      "The Effective Executive by Peter Drucker"
    ],
    "depth": "FULL"
  }'
```

### Query the library
```bash
curl -X POST https://your-app.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What does the library say about building habits?",
    "user_context": "New manager building team routines"
  }'
```

### Generate the Master Log
```bash
curl -X POST https://your-app.railway.app/master-log
```

### Search ideas
```bash
curl https://your-app.railway.app/ideas?q=attention
```

## Local Development

```bash
# Clone and set up
git clone https://github.com/YOUR_USERNAME/book-intelligence-agent.git
cd book-intelligence-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and DATABASE_URL

# Run locally
uvicorn main:app --reload --port 8000
```

Then visit http://localhost:8000/docs for the Swagger UI.
