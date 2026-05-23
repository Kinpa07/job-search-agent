from fastapi import FastAPI

app = FastAPI(title="Job Search Agent")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
