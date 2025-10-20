MAKEFLAGS += --no-print-directory --silent

################################################################################
# Makefile Variables
################################################################################
SHELL := $(or $(shell echo $$SHELL),/bin/sh)

VENV_PATH ?= .venv
POETRY_HOME ?= .venv_poetry

POETRY_VERSION = 1.8.3
PYTHON := $(shell if command -v pyenv >/dev/null 2>&1; then pyenv which python; else command -v python3; fi)
# PYTHON := $(shell pyenv which python)   # Force python version specified with .python-version
# PYTHON = $(shell command -v python3)    # Use system's python version

POETRY = $(POETRY_HOME)/bin/poetry

ALEMBIC_ROOT_DIR = src/fury_api/lib/db
ALEMBIC_CONFIG = $(ALEMBIC_ROOT_DIR)/alembic.ini
ALEMBIC_MIGRATIONS_DIR = $(ALEMBIC_ROOT_DIR)/migrations/versions

PYTHON_EXECUTABLE := PYTHONPATH=$(PWD)/src $(VENV_PATH)/bin/python

DOCKER_IMAGE = andrecavalheiro/beyond-gravity-usecase-api
DOCKERFILE_PATH = ./deploy/docker/fury_api.Dockerfile

KUBERNETES_CLUSTER = kratos
KUBERNETES_NAMESPACE = beyond-gravity-usecase

PROD_SECRETS_FILE = .env.prod

HELM_CHART_NAME = fury-api
HELM_CHART_PATH = ./deploy/helm

################################################################################
# Default
################################################################################
.DEFAULT_GOAL := default

.PHONY: default
default:
	@echo "Running default task"
	@$(MAKE) install
	@$(MAKE) format


################################################################################
# Setup & Install
################################################################################
.PHONY: install
install:
	$(MAKE) install-poetry
	$(MAKE) new-venv
	$(MAKE) install-deps
	$(MAKE) install-hooks

.PHONY: reinstall
reinstall:
	$(MAKE) delete-venv
	$(MAKE) remove-poetry
	$(MAKE) clean
	$(MAKE) install

.PHONY: install-poetry
install-poetry:
	@if [ -f "$(POETRY)" ]; then \
		echo "Poetry already installed in virtual environment"; \
	else \
		echo "Installing poetry in virtual environment"; \
		$(PYTHON) -m venv "$(POETRY_HOME)"; \
		$(POETRY_HOME)/bin/pip install --upgrade pip; \
		$(POETRY_HOME)/bin/pip install poetry==$(POETRY_VERSION); \
	fi

.PHONY: install-deps
-include .env
install-deps:
	@echo "Installing dependencies"
	@$(POETRY) install --no-root --no-interaction --no-ansi --all-extras -v


.PHONY: install-deps-no-extras
-include .env
install-deps-no-extras:
	@echo "Installing dependencies (no extras)"
	@$(POETRY) install --no-root --no-interaction --no-ansi -v


################################################################################
# Production - Install
################################################################################
.PHONY: prod-install
prod-install:
	$(MAKE) install-poetry
	$(MAKE) new-venv
	$(MAKE) install-deps-no-extras


################################################################################
# Development - Virtual Environment
################################################################################
.PHONY: new-venv
new-venv:
	@echo "Creating virtual environment"
	@$(PYTHON) -m venv "$(VENV_PATH)"

.PHONY: delete-venv
delete-venv:
	@echo "Deleting virtual environment"
	@rm -rf "$(VENV_PATH)"

.PHONY: remove-poetry
remove-poetry:
	@echo "Removing poetry from virtual environment"
	@rm -rf "$(POETRY_HOME)"


################################################################################
# Development - Utilities
################################################################################
.PHONY: clean
clean:
	@echo "Cleaning up"
	@rm -rf .pytest_cache .ruff_cache .coverage htmlcov/
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type f -name '*.py[co]' -delete
	@find . -type f -name '*~' -delete


################################################################################
# Development - Pre-commit Hooks
################################################################################
.PHONY: install-hooks
install-hooks:
	@echo "Installing pre-commit hooks"
	@$(POETRY) run pre-commit install

.PHONY: update-hooks
update-hooks:
	@echo "Updating pre-commit hooks"
	@$(POETRY) run pre-commit autoupdate


################################################################################
# Development - Dependencies
################################################################################
.PHONY: lock
lock:
	@echo "Locking dependencies"
	@$(POETRY) lock --no-update


################################################################################
# Database Migrations
################################################################################
.PHONY: db-create-migration
db-create-migration:
	@echo "Creating migration"
	@$(POETRY) run alembic --config $(ALEMBIC_CONFIG) revision --autogenerate -m "$(m)"
		$(POETRY) run ruff format $(ALEMBIC_MIGRATIONS_DIR) && \
		$(POETRY) run ruff check $(ALEMBIC_MIGRATIONS_DIR) --fix

.PHONY: db-migrate
db-migrate:
	@echo "Migrating database"
	@$(POETRY) run alembic --config $(ALEMBIC_CONFIG) upgrade head

# TODO: Maybe I can adjust the command bellow to use a differen port and avoid conflicts with local databases that might be running.
.PHONY: db-migrate-prod
db-migrate-prod:
	@$(MAKE) validate-context
	@echo "Starting port-forwarding for PostgreSQL..."
	@kubectl port-forward svc/fury-api-postgresql 5432:5432 &
	@sleep 3  # Give it a moment to establish the connection
	@echo "Running database migration..."
	@FURY_DB_URL=postgresql+psycopg://$$(grep -E '^FURY_DB_USER=' .env.prod | cut -d'=' -f2):$$(grep -E '^FURY_DB_PASSWORD=' .env.prod | cut -d'=' -f2)@127.0.0.1:5432/$$(grep -E '^FURY_DB_NAME=' .env.prod | cut -d'=' -f2) \
	$(POETRY) run alembic --config $(ALEMBIC_CONFIG) upgrade head
	@echo "Stopping port-forwarding..."
	@pkill -f "kubectl port-forward svc/fury-api-postgresql 5432:5432"

.PHONY: db-rollback
db-rollback:
	@echo "Rolling back database"
	@$(POETRY) run alembic --config $(ALEMBIC_CONFIG) downgrade -1

.PHONY: db-history
db-history:
	@$(POETRY) run alembic --config $(ALEMBIC_CONFIG) history

.PHONY: db-current
db-current:
	@$(POETRY) run alembic --config $(ALEMBIC_CONFIG) current

################################################################################
# Linting & Formatting
################################################################################
.PHONY: lint
lint:
	@echo "Running ruff check and format check"
	@$(POETRY) run ruff check . --exit-non-zero-on-fix
	@$(POETRY) run ruff format . --check

.PHONY: format
format:
	@echo "Running ruff format"
	@$(POETRY) run ruff format .
	@$(POETRY) run ruff check . --fix

.PHONY: autofix-unsafe
autofix-unsafe:
	@echo "Running ruff with autofix-unsafe"
	@$(POETRY) run ruff check . --unsafe-fixes


################################################################################
# Testing
################################################################################
test-ci: export FURY_DB_URL = postgresql+psycopg://postgres:postgres@postgres:5432/postgres
test-local: export FURY_DB_URL = postgresql+psycopg://postgres:postgres@127.0.0.1:5433/postgres

.PHONY: test
test:
	@if [ "$(CI)" = "true" ]; then \
		$(MAKE) test-ci; \
	else \
		$(MAKE) test-local; \
	fi

.PHONY: test-ci
test-ci:
	$(MAKE) FURY_DB_URL=$(FURY_DB_URL) db-migrate && \
	$(POETRY) run pytest -vvv;

.PHONY: test-local
test-local:
	echo "Starting PostgreSQL container on port 5433..."; \
	docker run --rm --name my_test_postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=postgres -p 5433:5432 -d postgres:15; \
	trap "echo 'Stopping and removing PostgreSQL container...'; docker stop my_test_postgres; " INT EXIT; \
	echo "Waiting for PostgreSQL to start..."; \
	sleep 2; \
	docker exec -it my_test_postgres sh -c "pg_isready -U postgres -h localhost -p 5432 -t 30"; \
	$(MAKE) FURY_DB_URL=$(FURY_DB_URL) db-migrate && \
	$(POETRY) run pytest -vvv;


################################################################################
# Devex
################################################################################
.PHONY: start
start:
	$(PYTHON_EXECUTABLE) -m fury_api

.PHONY: get-token
get-token:
	$(PYTHON_EXECUTABLE) fury_api.scripts.generate_firebase_token

.PHONY: generate-system-token
generate-system-token:
	@if [ -z "$(org_id)" ]; then \
		echo "Error: organization_id is required. Usage: make generate-system-token org_id=123 [user_id=456]"; \
		exit 1; \
	fi
	@if [ -z "$(user_id)" ]; then \
		$(PYTHON_EXECUTABLE) fury_api.scripts.generate_system_token $(org_id); \
	else \
		$(PYTHON_EXECUTABLE) fury_api.scripts.generate_system_token $(org_id) --user_id $(user_id); \
	fi

.PHONY: port-forward
port-forward:
	$(MAKE) validate-context  && \
	kubectl port-forward svc/fury-api-postgresql 5432:5432

################################################################################
# Deploy
################################################################################
.PHONY: deploy
deploy:
	$(MAKE) validate-context && \
	$(MAKE) docker-build-push && \
	$(MAKE) push-secrets && \
	$(MAKE) restart-deployment && \
	$(MAKE) db-migrate-prod && \
	printf "\nDeployment complete. Would you like to create a new tag? (y/N): "; \
	read confirm; \
	if [ "$$confirm" = "y" ]; then $(MAKE) tag; else echo "Skipping tag creation."; fi




.PHONY: set-context
set-context:
	@kubectl config use-context $(KUBERNETES_CLUSTER) || { echo "Error: Failed to switch to context '$(KUBERNETES_CLUSTER)'."; exit 1; }
	@kubectl config set-context --current --namespace=$(KUBERNETES_NAMESPACE) || { echo "Error: Failed to set namespace '$(KUBERNETES_NAMESPACE)'."; exit 1; }
	@echo "Switched to context '$(KUBERNETES_CLUSTER)' with namespace '$(KUBERNETES_NAMESPACE)'."


.PHONY: validate-context
validate-context:
	@CURRENT_CONTEXT=$$(kubectl config current-context); \
	CURRENT_NAMESPACE=$$(kubectl config view --minify --output 'jsonpath={..namespace}'); \
	if [ "$$CURRENT_CONTEXT" != "$(KUBERNETES_CLUSTER)" ]; then \
		echo "Error: Current context is not '$(KUBERNETES_CLUSTER)'. It is set to '$$CURRENT_CONTEXT'."; \
		exit 1; \
	fi; \
	if [ "$$CURRENT_NAMESPACE" != "$(KUBERNETES_NAMESPACE)" ]; then \
		echo "Error: Current namespace is not '$(KUBERNETES_NAMESPACE)'. It is set to '$$CURRENT_NAMESPACE'."; \
		exit 1; \
	fi

.PHONY: docker-build-push
docker-build-push:
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t $(DOCKER_IMAGE):latest \
		-f $(DOCKERFILE_PATH) \
		--push .

.PHONY: push-secrets
push-secrets: validate-context
	@kubectl create secret generic fury-api-env --from-env-file=$(PROD_SECRETS_FILE) -n $(KUBERNETES_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -

.PHONY: push-helm
push-helm:
	@$(MAKE) validate-context
	@if [ ! -f .env.prod ]; then echo "Error: .env.prod file not found!" && exit 1; fi
	@echo "Extracting DB credentials from .env.prod"
	@FURY_DB_USER=$$(grep -E '^FURY_DB_USER=' .env.prod | cut -d'=' -f2) && \
	 FURY_DB_PASSWORD=$$(grep -E '^FURY_DB_PASSWORD=' .env.prod | cut -d'=' -f2) && \
	 FURY_DB_NAME=$$(grep -E '^FURY_DB_NAME=' .env.prod | cut -d'=' -f2) && \
	 echo "Installing Helm Chart with user: $$FURY_DB_USER" && \
	 helm upgrade --install $(HELM_CHART_NAME) $(HELM_CHART_PATH) \
		--set postgresql.auth.username=$$FURY_DB_USER \
		--set postgresql.auth.password=$$FURY_DB_PASSWORD \
		--set postgresql.auth.database=$$FURY_DB_NAME

.PHONY: restart-deployment
restart-deployment:
	@$(MAKE) validate-context
	@kubectl rollout restart deployment fury-api


.PHONY: tag
tag:
	@latest_tag=$$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"); \
	version=$$(echo $$latest_tag | awk -F. '{print $$1 "." $$2 "." $$3+1}'); \
	if [ -z "$(m)" ]; then \
		printf "Enter a tag message: "; \
		read msg; \
	else \
		msg="$(m)"; \
	fi; \
	echo "Preparing to tag new version: $$version"; \
	printf "Confirm? (y/N): "; \
	read confirm; \
	if [ "$$confirm" != "y" ]; then echo "Aborted."; exit 1; fi; \
	git tag -a $$version -m "$$msg"; \
	git push origin --tags


################################################################################
# Production Access
################################################################################
.PHONY: prod-db-port-forward
prod-db-port-forward:
	$(MAKE) validate-context  && \
	kubectl port-forward svc/fury-api-postgresql 5432:5432

.PHONY: prod-logs
prod-logs:
	@$(MAKE) validate-context
	@echo "Tailing logs for pods with app.kubernetes.io/name=$(HELM_CHART_NAME) ..."
	@kubectl logs -f -l app.kubernetes.io/name=$(HELM_CHART_NAME) --tail=100
