PROD_HOST ?= $(shell grep -E '^PROD_VM_HOST=' .env | cut -d= -f2)
PROD_USER ?= $(shell grep -E '^PROD_VM_USER=' .env | cut -d= -f2)
SSH_KEY ?= ~/.ssh/google_compute_engine

tunnel:
	ssh -fN -i $(SSH_KEY) -L 5432:localhost:5432 $(PROD_USER)@$(PROD_HOST)
	@echo "Tunnel aberto: localhost:5432 -> $(PROD_HOST):5432"
	docker compose up -d ngrok

local: tunnel
	uv run uvicorn delpro_backend.main:app --host 0.0.0.0 --port 8000 --reload

stop:
	@pkill -f "ssh.*5432:localhost:5432" && echo "Tunnel fechado." || echo "Nenhum tunnel ativo."
	docker compose down

sync-env:
	gh secret set ENV_FILE --env production < .env
	@echo "ENV_FILE synced to GitHub Secrets (production)"

install-hooks:
	cp hooks/pre-push .git/hooks/pre-push
	chmod +x .git/hooks/pre-push
	@echo "pre-push hook installed"
