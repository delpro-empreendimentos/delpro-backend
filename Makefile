sync-env:
	gh secret set ENV_FILE --env production < .env
	@echo "ENV_FILE synced to GitHub Secrets (production)"

install-hooks:
	cp hooks/pre-push .git/hooks/pre-push
	chmod +x .git/hooks/pre-push
	@echo "pre-push hook installed"
