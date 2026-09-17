from pathlib import Path
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from graph import run_support_system_async

load_dotenv()

app = FastAPI(
    title="Harness Engineering Multi-Agent System",
    description="Production-grade multi-agent support harness with hybrid routing, telemetry, and structured validation",
    version="2.0.0"
)

BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)


class ChatRequest(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.post("/api/chat")
async def chat(data: ChatRequest):
    if not data.message or not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        result = await run_support_system_async(data.message.strip())
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": f"Execution failure: {str(e)}",
                "trace": [f"❌ Server Error: {str(e)}"]
            }
        )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )