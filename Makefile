# Noether — common dev commands.
.DEFAULT_GOAL := help

SHELL := bash

.PHONY: help up down logs ps test lint fmt typecheck eval eval-forecast eval-anomaly drift clean

help: ## list common targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## bring up the core dev stack
	docker compose --profile core up -d

down: ## tear down the dev stack and remove volumes
	docker compose --profile core --profile eval --profile cron --profile agent down -v

logs: ## tail logs from every service
	docker compose --profile core logs -f --tail=100

ps: ## list running containers
	docker compose --profile core ps

test: ## run pytest with coverage
	uv run --dev pytest

lint: ## run ruff
	uv run --dev ruff check .

fmt: ## format with black + ruff
	uv run --dev black .
	uv run --dev ruff check --fix .

typecheck: ## run mypy
	uv run --dev mypy libs services

eval: eval-forecast eval-anomaly ## run both eval harnesses (forecast + anomaly)

eval-forecast: ## run the forecast eval harness in a one-shot container
	docker compose --profile eval run --rm forecast-eval

eval-anomaly: ## run the anomaly-detection eval harness in a one-shot container
	docker compose --profile eval run --rm anomaly-eval

drift: ## run the Evidently drift job once (one-shot, prints summary)
	docker compose --profile cron run --rm --entrypoint python drift -m noether_drift

clean: ## drop pycache + build artefacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist
