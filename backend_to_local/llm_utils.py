import requests
import time

OLLAMA_API_URL = "http://localhost:11434/api/generate"

def query_llm(prompt: str, model_name: str = "mistral") -> str:
    try:
        start_time = time.time()
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
            },
            timeout=600
        )
        duration = time.time() - start_time
        print(f"[INFO] LLM response time: {duration:.2f} seconds")
        result = response.json()
        return result.get("response", "No answer returned.")
    except Exception as e:
        raise RuntimeError(f"Inference error: {e}")