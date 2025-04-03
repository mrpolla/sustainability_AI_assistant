import requests
import time

OLLAMA_API_URL = "https://3nxdf6233n8u8w-8000.proxy.runpod.net/api/generate"

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
        print(f"[DEBUG] Raw response text: {response.text}")

        result = response.json()
        return result.get("response", "No answer returned.")
    except Exception as e:
        print(f"[ERROR] Inference error: {e}")
        raise RuntimeError(f"Inference error: {e}")