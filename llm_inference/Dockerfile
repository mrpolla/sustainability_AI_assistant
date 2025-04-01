FROM python:3.10-slim

# Install Ollama
RUN apt-get update && apt-get install -y curl gnupg \
  && curl -fsSL https://ollama.com/install.sh | sh \
  && apt-get clean

# Expose Ollama and API port
EXPOSE 11434

# Copy files
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .


# Start Ollama + FastAPI
ENV MODEL_NAME=mistral
CMD bash -c "ollama serve & sleep 3 && ollama run $MODEL_NAME && uvicorn main:app --host 0.0.0.0 --port 8000"