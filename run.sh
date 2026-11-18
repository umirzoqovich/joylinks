#!/usr/bin/env bash
# Joylinks CRM - Linux / VPS ishga tushirish skripti
set -e
echo "🚀 Joylinks Target CRM ishga tushirilmoqda..."
if [ ! -d ".venv" ]; then
    echo "Virtual environment yaratilmoqda..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

python3 run.py
