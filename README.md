<div align="center">
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" />
  <img src="https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <h1>DevKit.AI — API Gateway & Backend</h1>
  <p>The high-performance central router and state manager for DevKit.AI.</p>
</div>

---

## 📌 Overview
This repository serves as the **API Gateway and Backend** for DevKit.AI. Built with FastAPI, it acts as the vital bridge between the interactive React frontend and the heavy-duty LLM Engine gRPC microservice.

It is responsible for maintaining stateful conversational context, proxying WebSocket connections for the AI Discovery Engine, and providing low-latency Server-Sent Events (SSE) streaming.

## 🏗️ System Architecture & Data Flow

```mermaid
sequenceDiagram
    participant F as Next-Gen Frontend (React)
    participant B as FastAPI Gateway
    participant DB as MongoDB
    participant LLM as gRPC LLM Engine

    Note over F,LLM: 1. Session Initialization
    F->>B: POST /session/start
    B->>DB: Create Session (Store initial context)
    B-->>F: Return `session_id`

    Note over F,LLM: 2. Interactive Discovery Phase
    F->>B: Connect to WebSocket `/ws/session/{session_id}`
    B->>LLM: DecideNextAction(session_data)
    LLM-->>B: Yield questions & phase updates
    B-->>F: Push questions to user UI
    F->>B: User submits answers (or skips)
    B->>DB: Save answers to Phase state

    Note over F,LLM: 3. Blueprint Generation (Streaming)
    F->>B: GET /stream/generate/{session_id}
    B->>LLM: CompileFinalBrief() & RunSwarm()
    LLM-->>B: Stream Events (Architect, PM, Prompt)
    B-->>F: Server-Sent Events (SSE) stream back to UI
    B->>DB: Save Final Generated Outputs
```

## ✨ Core Features
- **Real-Time Blueprint Streaming**: Exposes `/stream/generate` endpoints that stream real-time Server-Sent Events (SSE) from the AI swarm back to the frontend.
- **Stateful Session Management**: Uses `motor` (AsyncIOMotorClient) to track user interviews across 6 distinct phases (UI/UX, Core Logic, Architecture, Security, Testing, Deployment).
- **Natural Language Refinement**: Handles conversational modifications to existing blueprints and strategically patches the JSON document without requiring a full LLM re-run.
- **Artifact Exporting**: Instantly compiles the generated JSON blueprints into downloadable Markdown assets (VC Pitch Decks, Implementation Instructions) and automated ZIP Boilerplates.

## 🚀 Quick Start & Local Development

### 1. Prerequisites
- Python 3.10+
- A running MongoDB instance (Local or Atlas)

### 2. Installation
Navigate into the `Backend` directory and install the required dependencies:
```bash
cd Backend
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration
You need to provide a MongoDB connection string.
```bash
# Set your environment variable for the database connection
export MONGODB_URI="mongodb://localhost:27017" # Or your MongoDB Atlas URI
```

### 4. Running the Server
Launch the FastAPI application using Uvicorn:
```bash
uvicorn main:app --reload --port 8000
```
*The API Gateway will now be accessible at `http://localhost:8000`. You can view the automatic Swagger documentation at `http://localhost:8000/docs`.*

---

## 📁 Directory Structure
- `/api/routes.py` — Core endpoint definitions (REST, WebSockets, SSE streams).
- `/core/session_manager.py` — MongoDB CRUD operations and session state handlers.
- `/core/grpc_clients.py` — The client stubs that communicate with the LLM gRPC Engine.
- `/routes/` — Modular endpoint logic for exporting pitch decks and boilerplate ZIP files.
