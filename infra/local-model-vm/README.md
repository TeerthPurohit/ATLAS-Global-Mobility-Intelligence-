# Local QueryPlan model VM (Oracle Always-Free)

## Provision (Oracle Cloud console, one-time)

1. Sign up / log in at cloud.oracle.com. Create a Compute instance:
   Shape = VM.Standard.A1.Flex (Always Free eligible), 4 OCPU / 24GB RAM,
   Ubuntu 24.04 image.
2. Note the instance's public IP.
3. Networking → the instance's VCN → Security Lists → default security
   list → Add Ingress Rule: source `0.0.0.0/0` (or narrower if you have a
   known backend egress range), TCP, destination port `8080`.
4. SSH in: `ssh ubuntu@<public-ip>`.

## Install + start (on the VM)

    scp infra/local-model-vm/setup.sh ubuntu@<public-ip>:~/
    scp models/query_plan_finetune/gguf/queryplan-q4_k_m.gguf ubuntu@<public-ip>:~/model.gguf
    ssh ubuntu@<public-ip> 'LLAMA_API_KEY=<generate-a-real-token> bash setup.sh'

`setup.sh` builds llama.cpp, installs the systemd unit, and starts it.
Generate the token with e.g. `openssl rand -hex 32` — put the same value
in this repo's `.env` as `LOCAL_MODEL_API_KEY` (Task 5 reads it from there).

## Verify

    curl http://<public-ip>:8080/v1/chat/completions \
      -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
      -d '{"model": "queryplan", "messages": [{"role": "user", "content": "hi"}]}'

Expected: a valid chat-completion JSON response, not a 401.
