#!/bin/bash
# Duplo-clique para abrir o site da Carteira.
cd "$(dirname "$0")/backend"
echo "Iniciando o site da carteira..."
"../.venv/bin/python" -m uvicorn app:app --host 127.0.0.1 --port 8848 &
SERVER_PID=$!
sleep 2
open "http://127.0.0.1:8848/"
echo ""
echo "Site aberto no navegador: http://127.0.0.1:8848/"
echo "Para PARAR o site, feche esta janela ou pressione Ctrl+C."
wait $SERVER_PID
