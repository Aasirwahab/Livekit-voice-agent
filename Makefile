.PHONY: format lint type-check test test-parallel clean help dev-setup

format:
	@echo "Formatting code with ruff..."
	uv run ruff format .

lint:
	@echo "Linting code with ruff..."
	uv run ruff check --output-format=github .

type-check:
	@echo "Running type checking with mypy..."
	uv run mypy src/

test:
	@echo "Running tests..."
	uv run pytest -v

test-parallel:
	@echo "Running tests in parallel..."
	uv run pytest -v -n auto

test-coverage:
	@echo "Running tests with coverage..."
	uv run pytest --cov=src --cov-report=html --cov-report=term

clean:
	@echo "Cleaning up cache directories..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .coverage -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true

dev-setup:
	@echo "Setting up development environment..."
	uv sync --dev
	@echo "Development environment ready!"

check-all: lint type-check test
	@echo "✓ All checks passed!"

fix:
	@echo "Fixing code formatting and style issues..."
	uv run ruff format .
	uv run ruff check --fix .
	@echo "✓ Fixed!"

help:
	@echo "Available commands:"
	@echo "  make format         - Format code with ruff"
	@echo "  make lint           - Lint code with ruff"
	@echo "  make type-check     - Run mypy type checking"
	@echo "  make test           - Run tests with pytest"
	@echo "  make test-parallel  - Run tests in parallel with pytest-xdist"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make check-all      - Run all checks (lint, type-check, test)"
	@echo "  make fix            - Auto-fix formatting and style issues"
	@echo "  make clean          - Remove cache directories"
	@echo "  make dev-setup      - Set up development environment"
	@echo "  make help           - Show this help message"
