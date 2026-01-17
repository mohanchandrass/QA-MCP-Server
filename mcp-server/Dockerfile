# -------------------------------------------------------
# Knowledge-Powered Q&A and Action Bot MCP Server
# Docker Image 
#
# - Lightweight Python base
# - Multi-stage build for smaller image
# - Externalized configs (persona / intents / actions)
# - Knowledge base mounted at runtime
# - Exposes MCP HTTP endpoint on port 8000
# -------------------------------------------------------

# ---------- Stage 1: Build ----------
FROM python:3.11-slim AS builder

WORKDIR /app
    
ENV DEBIAN_FRONTEND=noninteractive
    
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
    
# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim
    
WORKDIR /app
    
# Copy only installed deps
COPY --from=builder /install /usr/local
    
# Copy MCP server code only (NO CONFIGS)
COPY qa_mcp_server.py .
    
# Expose MCP port
EXPOSE 8000
    
# Unbuffered output is REQUIRED for MCP
ENTRYPOINT ["python", "-u", "qa_mcp_server.py"]
    