#!/usr/bin/env bash
# infra/local-model-vm/setup.sh -- run ON the Oracle VM as the ubuntu user.
set -euo pipefail

: "${LLAMA_API_KEY:?set LLAMA_API_KEY before running}"

sudo apt-get update && sudo apt-get install -y build-essential cmake git

if [ ! -d ~/llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp ~/llama.cpp
fi
cmake -B ~/llama.cpp/build -S ~/llama.cpp -DCMAKE_BUILD_TYPE=Release
cmake --build ~/llama.cpp/build --config Release -j "$(nproc)"

sudo mkdir -p /opt/queryplan-model
sudo mv ~/model.gguf /opt/queryplan-model/model.gguf

sudo tee /etc/systemd/system/llama-server.service > /dev/null <<EOF
[Unit]
Description=llama.cpp server (QueryPlan model)
After=network.target

[Service]
ExecStart=$HOME/llama.cpp/build/bin/llama-server -m /opt/queryplan-model/model.gguf -c 2048 --host 0.0.0.0 --port 8080 --api-key $LLAMA_API_KEY
Restart=always
RestartSec=5
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now llama-server.service
echo "llama-server started, status:"
sudo systemctl status llama-server.service --no-pager
