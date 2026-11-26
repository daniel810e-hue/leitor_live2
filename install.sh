#!/data/data/com.termux/files/usr/bin/bash
# Instalador do leitor_live_site2.py (Termux)

cd "$(dirname "$0")" || exit 1

echo "Instalando dependências..."
pkg update -y
pkg install -y python

pip install requests

echo "Liberando acesso ao armazenamento (aceite a permissão na tela)..."
termux-setup-storage
sleep 5

echo "Iniciando o leitor..."
python leitor_live_site2.py
