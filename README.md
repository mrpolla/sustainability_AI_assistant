# ♻️ LLM-Based Sustainability Assistant for EPD Analysis

This project is an AI-powered system for analyzing and comparing Environmental Product Declarations (EPDs). It integrates structured data, semantic embeddings, and large language models (LLMs) to extract, enrich, and query sustainability-related information.

---

## 📌 Project Goals

- Ingest and store EPD data from XML and PDF sources
- Enrich incomplete product information using LLMs
- Enable semantic search and comparison across indicators, materials, and categories
- Provide a fast, interactive frontend for analysis and Q&A

---

## ✅ MVP (Minimum Viable Product)

### 📥 Data Collection & Storage
- Retrieved EPD data using **Selenium**, parsed **XML**.
- Stored structured product and indicator data in **PostgreSQL**.

### 🧠 Local LLM Experiments
- Tested **Mistral-7B-Instruct (quantized)** locally.
- Built a basic **React + FastAPI** full-stack prototype.
- Used `all-MiniLM-L6-v2` for initial embeddings.
- Switched to **Ollama** with `nous-hermes2` due to poor results and slow inference (60s per request).

---

## 🧪 Development Phase

### ⚡ Inference Optimization
- Deployed a prebuilt **Ollama container** on **RunPod** using:
  - **RTX 2000 Ada GPU**, 16 GB VRAM, 31 GB RAM, 100 GB disk
- Benchmarked multiple LLMs:
  - Mistral (7B), LLaMA3 (8B), Gemma, Qwen, Phi-3
- **Selected Mistral** for consistent performance.

### 🧱 Text Processing & Embedding
- Extracted text manually from PDFs and saved as `.txt`.
- **Programmatically chunked** into 3–4 sentence segments.
- Checked chunks for semantic relevance using LLM.
- Embedded with `bge-small-en-v1.5` (384 dimensions).
- Stored in PostgreSQL using **pgvector**.

### 🧽 Data Enrichment & Cleanup
- Filled missing English descriptions using LLM-based **German translation**.
- Inferred **material** and **use-case** from unstructured text.
- Generated **statistics (mean, min, max, range)** for indicators by category for fast retrieval.

---

## 🚀 Final System Architecture

### 💻 Frontend – React
- Filters products by:
  - **Indicator**, **Category**, **Material**, **Use Case**
- Retrieves:
  - Structured product/indicator data from PostgreSQL
  - Embedded chunks from EPD XML and theory PDFs (via pgvector)
- Sends questions to FastAPI for:
  - **LLM-based classification**
  - **Routed LLM answers**

### 🧠 Backend – FastAPI
- Interfaces with both the database and LLM.
- Handles:
  - PostgreSQL queries for structured + embedded data
  - pgvector semantic retrieval
  - LLM prompt generation and routing

### 🗄️ Database – PostgreSQL + pgvector
- Stores:
  - Parsed XML product data
  - Chunked and embedded EPD text and theory documents
- Enables:
  - Standard SQL queries
  - **Vector similarity search** for semantic context

### 🤖 LLM Backend – RunPod/Ollama
- Hosts **Mistral (7B quantized)**
- Handles:
  - Question classification
  - Answer generation using retrieved context
- Communicates with FastAPI via prompt/response API

---

## 📎 Tech Stack

| Component   | Tech |
|-------------|------|
| Frontend    | React |
| Backend     | FastAPI |
| Database    | PostgreSQL + pgvector |
| Embeddings  | `bge-small-en-v1.5` |
| LLMs        | Mistral, LLaMA3, etc. via Ollama on RunPod |

---

## 📂 Folder Structure (Suggested)

