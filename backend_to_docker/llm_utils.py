import requests
import time

OLLAMA_API_URL = "https://3nxdf6233n8u8w-8000.proxy.runpod.net/api/generate"

def query_llm(prompt: str, model_name: str = "mistral") -> str:
    """
    Query an LLM with the given prompt using the specified model.
    
    :param prompt: The input prompt for the LLM
    :param model_name: The name of the model to use (mapped to Ollama model)
    :return: The generated response from the LLM
    """
    # Model mapping to Ollama models
    model_mapping = {
        "llama3.1": "llama3.1",
        "mistral": "mistral",
        "llama3.1-3b": "llama3.1-3b",
        # Frontend model names mapped to Ollama models
        "Llama-3.2-1B-Instruct": "llama3.1",
        "Mistral-7B-Instruct-v0.2": "mistral", 
        "Llama-3.2-3B": "llama3.1-3b"
    }
    
    # Normalize the model name
    normalized_model = model_mapping.get(model_name, "mistral")
    try:
        start_time = time.time()
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": normalized_model,
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