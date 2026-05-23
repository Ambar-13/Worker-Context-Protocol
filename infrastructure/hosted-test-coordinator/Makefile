# WCP hosted test coordinator: common operator commands.
#
# Targets are intentionally small; each one does one thing. Operators
# wrap these in their own runbooks for fleet-wide actions.

SHELL := /bin/bash
ENV_FILE := secrets/.env
COMPOSE := docker compose --env-file $(ENV_FILE)

.PHONY: help up down restart logs health migrate rotate-keys wipe

help:
	@echo "Targets:"
	@echo "  up           - bring up the stack"
	@echo "  down         - stop services (keeps volumes)"
	@echo "  restart      - restart all services"
	@echo "  logs         - tail aggregate logs"
	@echo "  health       - hit /health on the coordinator"
	@echo "  migrate      - run coordinator schema migrations"
	@echo "  rotate-keys  - generate a new coordinator signing key"
	@echo "  wipe         - DESTRUCTIVE: remove volumes and keys"

up: $(ENV_FILE) secrets/coordinator.ed25519
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f --tail=100

health:
	@set -e; \
	host=$$(grep ^PUBLIC_HOSTNAME $(ENV_FILE) | cut -d= -f2); \
	curl -fsS https://$$host/health | tee /dev/stderr

migrate:
	$(COMPOSE) exec coordinator wcp-coordinator migrate

rotate-keys:
	@if [ -f secrets/coordinator.ed25519 ]; then \
		mv secrets/coordinator.ed25519 secrets/coordinator.ed25519.prev; \
	fi
	wcp identity create --key-out secrets/coordinator.ed25519
	@echo "New key written. Restart the coordinator within the key-overlap window."

wipe:
	@echo "DESTRUCTIVE. Press Ctrl-C in the next 5s to cancel..."
	@sleep 5
	$(COMPOSE) down -v
	rm -f secrets/coordinator.ed25519 secrets/coordinator.ed25519.prev

$(ENV_FILE):
	@echo "ERROR: $(ENV_FILE) not found."
	@echo "       cp secrets/.env.example secrets/.env, then edit."
	@exit 1

secrets/coordinator.ed25519:
	@echo "Generating a coordinator signing key. Back this up offline."
	wcp identity create --key-out $@
