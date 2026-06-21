# DevKit.AI — API Gateway & Backend

This repository serves as the primary API Gateway and Backend for DevKit.AI. Built with FastAPI (Python), it acts as the central router between the Next.js frontend clients and the heavy-duty LLM Engine gRPC microservice.

## Architecture
- **FastAPI Framework**: Provides high-performance, asynchronous REST API endpoints.
- **MongoDB Integration**: Uses `motor` (AsyncIOMotorClient) to persist user sessions, blueprint generations, and conversational refinement history.
- **gRPC Client**: Interacts with the multi-agent LLM Engine via highly optimized protobuf-defined gRPC channels.
- **Server-Sent Events (SSE)**: Streams real-time, event-driven updates from the LLM swarm back to the frontend, allowing users to watch the AI build their architecture, milestones, and instructions live.

## Features
- **Session Management**: Tracks user state across the 6-phase interview process.
- **Blueprint Streaming**: Exposes `/stream/generate` endpoints for instant feedback.
- **Refinement API**: Handles natural-language modifications to existing blueprints and merges JSON patches.
- **Artifact Export**: Compiles generated JSON artifacts into Markdown downloads (Pitch Deck, Implementation Instructions).

## Deployment
This service is designed to be deployed using PM2 or Docker. Ensure that the `MONGODB_URI` environment variable is configured and the LLM Engine is accessible on the designated `GRPC_PORT`.
