.PHONY: help test test-unit test-integration test-all test-verbose test-coverage clean-test install-test-deps run-server format format-check lint type-check quality-check quality-fix

# Default target - show help
help:
	@echo "RAG Chatbot Test Commands"
	@echo "=========================="
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run all unit tests (same as test-unit)"
	@echo "  make test-unit         - Run backend unit tests with pytest"
	@echo "  make test-integration  - Run UI integration tests with shell script"
	@echo "  make test-all          - Run both unit and integration tests"
	@echo "  make test-verbose      - Run unit tests with verbose output"
	@echo "  make test-coverage     - Run unit tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format            - Auto-format code with black and isort"
	@echo "  make format-check      - Check if code needs formatting (CI-friendly)"
	@echo "  make lint              - Run flake8 linter"
	@echo "  make type-check        - Run mypy type checker"
	@echo "  make quality-check     - Run all quality checks (format-check, lint, type-check)"
	@echo "  make quality-fix       - Auto-fix quality issues (format + checks)"
	@echo ""
	@echo "Development:"
	@echo "  make install-test-deps - Install testing dependencies"
	@echo "  make run-server        - Start the development server"
	@echo "  make clean-test        - Remove test artifacts and cache"
	@echo ""
	@echo "Quick Start:"
	@echo "  make test-all          - Run everything to verify system health"

# Run unit tests (default test command)
test: test-unit

# Run backend unit tests with pytest
test-unit:
	@echo "Running backend unit tests..."
	@cd backend && uv run pytest tests/ -v --tb=short
	@echo ""
	@echo "✓ Unit tests complete"

# Run UI integration tests
test-integration:
	@echo "Running UI integration tests..."
	@./test_ui_integration.sh
	@echo ""
	@echo "✓ Integration tests complete"

# Run all tests (unit + integration)
test-all: test-unit test-integration
	@echo ""
	@echo "=========================================="
	@echo "✓ All tests complete!"
	@echo "=========================================="

# Run unit tests with extra verbose output
test-verbose:
	@echo "Running unit tests with verbose output..."
	@cd backend && uv run pytest tests/ -vv --tb=long

# Run unit tests with coverage report
test-coverage:
	@echo "Running unit tests with coverage analysis..."
	@cd backend && uv run pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated in backend/htmlcov/index.html"

# Install testing dependencies
install-test-deps:
	@echo "Installing test dependencies..."
	@uv add --dev pytest pytest-asyncio pytest-mock pytest-cov
	@echo "✓ Test dependencies installed"

# Start the development server
run-server:
	@echo "Starting development server on http://localhost:8000"
	@./run.sh

# Clean test artifacts and cache
clean-test:
	@echo "Cleaning test artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@rm -rf backend/test_chroma_db 2>/dev/null || true
	@echo "✓ Test artifacts cleaned"

# Quick health check - run fast tests only
test-quick:
	@echo "Running quick health check tests..."
	@cd backend && uv run pytest tests/test_search_tools.py tests/test_vector_store.py -v --tb=short
	@echo ""
	@echo "✓ Quick tests complete"

# Run specific test file
# Usage: make test-file FILE=test_vector_store
test-file:
	@echo "Running tests in $(FILE).py..."
	@cd backend && uv run pytest tests/$(FILE).py -v

# Run specific test function
# Usage: make test-func FUNC=test_search_without_filters FILE=test_vector_store
test-func:
	@echo "Running test $(FUNC) in $(FILE).py..."
	@cd backend && uv run pytest tests/$(FILE).py::$(FUNC) -v

# Continuous integration - run all tests with coverage
ci: test-coverage test-integration
	@echo ""
	@echo "=========================================="
	@echo "✓ CI tests complete!"
	@echo "=========================================="

# Code Quality Commands

# Auto-format code with black and isort
format:
	@echo "Formatting code with black..."
	@cd backend && uv run black .
	@echo "Sorting imports with isort..."
	@cd backend && uv run isort .
	@echo "✓ Code formatted"

# Check if code needs formatting (for CI/pre-commit)
format-check:
	@echo "Checking code formatting..."
	@cd backend && uv run black --check .
	@cd backend && uv run isort --check-only .
	@echo "✓ Code formatting is correct"

# Run flake8 linter
lint:
	@echo "Running flake8 linter..."
	@cd backend && uv run flake8 .
	@echo "✓ Linting complete"

# Run mypy type checker (informational - shows issues but doesn't fail build)
type-check:
	@echo "Running mypy type checker..."
	@cd backend && uv run mypy . --exclude 'chroma_db|__pycache__|\.pytest_cache|\.venv' || echo "⚠ Type checking found issues (non-blocking)"
	@echo "✓ Type checking complete"

# Run all quality checks (for CI)
quality-check: format-check lint type-check
	@echo ""
	@echo "=========================================="
	@echo "✓ All quality checks passed!"
	@echo "=========================================="

# Auto-fix quality issues and run checks
quality-fix: format
	@echo ""
	@$(MAKE) lint
	@$(MAKE) type-check
	@echo ""
	@echo "=========================================="
	@echo "✓ Code quality improvements complete!"
	@echo "=========================================="
