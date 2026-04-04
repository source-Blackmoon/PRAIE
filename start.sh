#!/bin/bash
# start.sh — Levanta el backend y el frontend de PRAIE

BACKEND_PORT=8001
FRONTEND_PORT=4001
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cleanup() {
  echo -e "\n${YELLOW}Deteniendo servicios...${NC}"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  echo -e "${GREEN}Listo.${NC}"
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── Backend ───────────────────────────────────────────────
echo -e "${GREEN}▶ Iniciando backend (puerto $BACKEND_PORT)...${NC}"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  echo -e "${RED}Error: no se encontró .venv en $SCRIPT_DIR${NC}"
  exit 1
fi

.venv/bin/uvicorn agent.main:app --port "$BACKEND_PORT" --reload \
  > /tmp/praie-backend.log 2>&1 &
BACKEND_PID=$!

echo -n "  Esperando backend"
for i in $(seq 1 15); do
  sleep 1
  if .venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://localhost:$BACKEND_PORT/')" 2>/dev/null; then
    echo -e " ${GREEN}✓${NC}"
    break
  fi
  echo -n "."
  if [ "$i" -eq 15 ]; then
    echo -e " ${RED}✗ timeout — revisa /tmp/praie-backend.log${NC}"
    cleanup
  fi
done

# ── Frontend ──────────────────────────────────────────────
echo -e "${GREEN}▶ Iniciando frontend (puerto $FRONTEND_PORT)...${NC}"
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
  echo "  Instalando dependencias npm..."
  npm install --silent
fi

npm run dev > /tmp/praie-frontend.log 2>&1 &
FRONTEND_PID=$!

echo -n "  Esperando frontend"
for i in $(seq 1 20); do
  sleep 1
  if grep -q "Ready" /tmp/praie-frontend.log 2>/dev/null; then
    echo -e " ${GREEN}✓${NC}"
    break
  fi
  echo -n "."
done
echo ""

# ── Resumen ───────────────────────────────────────────────
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  PRAIE — Panel Laura${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Dashboard:  ${YELLOW}http://localhost:$FRONTEND_PORT${NC}"
echo -e "  Backend:    ${YELLOW}http://localhost:$BACKEND_PORT${NC}"
echo -e "  Logs:       tail -f /tmp/praie-backend.log"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Ctrl+C para detener todo\n"

wait "$BACKEND_PID" "$FRONTEND_PID"
