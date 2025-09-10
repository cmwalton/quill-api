from fastapi import FastAPI

app = FastAPI(title="Quill API", version="v1")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ai/complete")
def ai_complete(prompt: str):
    # Baby step: just echo the prompt for now
    return {"response": f"You asked me to complete: {prompt}"}
