# FastAPI First Steps

This introductory application exposes `GET /` and returns a JSON greeting.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the generated interactive API documentation.
