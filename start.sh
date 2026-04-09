#!/usr/bin/env bash
# ============================================================
# ProcureAI — Backend Quick Start
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       ProcureAI — Starting Backend        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
  if [ -f "$BACKEND_DIR/.env" ]; then
    echo "✓ Loading .env file"
    set -a
    source "$BACKEND_DIR/.env"
    set +a
  else
    echo "✗ ANTHROPIC_API_KEY not set and no .env file found."
    echo ""
    echo "  Option 1: export ANTHROPIC_API_KEY=sk-ant-..."
    echo "  Option 2: cp backend/.env.example backend/.env && edit backend/.env"
    echo ""
    exit 1
  fi
fi

echo "✓ Anthropic API key found"
echo "✓ Starting FastAPI on http://localhost:8000"
echo "✓ Swagger UI at  http://localhost:8000/docs"
echo ""

cd "$BACKEND_DIR"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
