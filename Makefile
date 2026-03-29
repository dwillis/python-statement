.PHONY: test install clean generate-legislators health health-quick trend dashboard help

help:
	@echo "Available commands:"
	@echo "  make install              - Install dependencies using uv"
	@echo "  make test                 - Run all tests"
	@echo "  make clean                - Clean build artifacts and cache files"
	@echo "  make generate-legislators - Generate legislators_with_scrapers.json"
	@echo "  make health               - Run full scraper health check (all scrapers)"
	@echo "  make health-quick         - Run quick scraper health check (~50 scrapers)"
	@echo "  make dashboard            - Build static health dashboard (docs/index.html)"
	@echo "  make trend                - View health trends over time"

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

health:
	uv run python scripts/run_health_check.py --full --save

health-quick:
	uv run python scripts/run_health_check.py --save

trend:
	uv run python scripts/health_trend.py

dashboard:
	uv run python scripts/build_dashboard.py
