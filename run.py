"""One command, one server (frontend + API together):  python run.py  ->  http://127.0.0.1:8000"""
import uvicorn

if __name__ == "__main__":
    print("Open http://127.0.0.1:8000  (use Chrome for voice)")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
