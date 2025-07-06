# 🧠 McDonald's Outlets AI Backend (FastAPI + Ollama + Supabase)

This is the backend API for McDonald’s outlet search and AI Q&A system built using:
- **FastAPI**
- **Ollama** (LLaMA3.2 + nomic-embed-text)
- **pgvector** with **Supabase (PostgreSQL)**

---

## ⚙️ Requirements

- Python 3.11+
- PostgreSQL
- Ollama (llama3.2 + nomic-embed-text)

---

## 📝 Technologies

- [FastAPI](https://fastapi.tiangolo.com)
- [pgvector](https://supabase.com/docs/guides/vector-database)
- [Supabase](https://supabase.com)
- [Ollama](https://ollama.com) installed locally with:
  - `ollama pull llama3.2`
  - `ollama pull nomic-embed-text`

---

## 🔧 Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/mcd-ai-backend.git
cd mcd-ai-backend
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a new PostgreSQL database

Create a new PostgreSQL database and configure the `DATABASE_URL` environment variable in the `.env` file.

### 4. Run migrations

```bash
alembic upgrade head

# Optional: create new migration file
alembic revision --autogenerate -m "create outlets"
```


### 5. Run the scraper

If you have the scraper, run it to scrape McDonald's outlets:

```bash
python -m scripts.mcdonalds_scraper
```

### 6. Upload outlet data to DB

```bash
python -m scripts.upload_outlets
```

### 7. Generate and upload embeddings to pgvector

```bash
python -m scripts.upload_vector
```

### 8. Calculate outlet proximity (for 5km catchment)

```bash
python -m scripts.process_proximity
```

### 9. Start the server

```bash
ollama serve
ollama pull llama3.2
ollama pull nomic-embed-text
```

```bash
fastapi dev main.py
```
