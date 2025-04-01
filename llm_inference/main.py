from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from llm_inference.llm_utils import query_llm

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str
    model: str = "mistral"

@app.post("/api/generate")
async def generate(req: PromptRequest):
    response = query_llm(req.prompt, req.model)
    return JSONResponse({"response": response})
