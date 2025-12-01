.PHONY: test install clean generate-legislators compare help

help:
	@echo "Available commands:"
	@echo "  make install              - Install dependencies using uv"
	@echo "  make test                 - Run all tests"
	@echo "  make clean                - Clean build artifacts and cache files"
	@echo "  make generate-legislators - Generate legislators_with_scrapers.json"
	@echo "  make compare              - Compare Python implementation with Ruby"

install:
	uv sync

test:
	uv run pytest tests/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

generate-legislators:
	uv run python scripts/generate_legislators.py

compare:
	uv run python scripts/comprehensive_compare.py
