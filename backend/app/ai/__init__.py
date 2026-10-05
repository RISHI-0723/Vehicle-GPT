"""VehicleGPT AI service layer (Sprint 4).

Architecture: React -> FastAPI -> this package -> Ollama (llama3.1:8b).

This package NEVER calculates vehicle intelligence itself. It routes a
driver's question to a deterministic intent, fetches the matching Sprint 2
intelligence result, and asks a local LLM to explain that result in
natural language. If the LLM is unavailable, times out, or returns
malformed output, a deterministic fallback formatter is used instead so
the product keeps working without any AI provider.
"""
