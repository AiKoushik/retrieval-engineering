# Companion code for Retrieval Engineering. `make` lists the targets.
# The Python commands read RX_DSN and RX_TEST_DSN (rx/config.py); the
# psql targets read PGHOST, PGPORT and PGUSER, e.g.
#   make db PGHOST=localhost        # Postgres in Docker

PYTHON ?= python3
PGHOST ?= /tmp
PGUSER ?= postgres
PSQL = psql -h $(PGHOST) -U $(PGUSER) -v ON_ERROR_STOP=1
# scratch databases the commands create (rx_b1, rx_ch06, rx_appB, ...)
SCRATCH = ^rx_(b[0-9]|ch[0-9][0-9]|app[A-Z])$$

.DEFAULT_GOAL := help
.PHONY: help install clean

help:                   ## list the targets
	@grep -hE '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | \
	  sed -E 's/:[^#]*## /\t/' | expand -t 18

install:                ## the exact library versions, then this code
	$(PYTHON) -m pip install -r requirements.lock
	$(PYTHON) -m pip install --no-deps -e .

.PHONY: test
test:                   ## every test (Postgres tests need RX_TEST_DSN)
	$(PYTHON) -m pytest -q

.PHONY: test-fast db drop-scratch
test-fast:              ## fast tests: no database, no generator runs
	$(PYTHON) -m pytest -q -m "not db and not slow"

db:                     ## create the empty databases rx and rx_test
	for name in rx rx_test; do \
	  $(PSQL) -d postgres -tc \
	    "SELECT 1 FROM pg_database WHERE datname = '$$name'" \
	    | grep -q 1 || $(PSQL) -d postgres -c "CREATE DATABASE $$name"; \
	done

drop-scratch:           ## drop the scratch databases (never rx, rx_test)
	for name in $$($(PSQL) -d postgres -Atc "SELECT datname FROM \
	    pg_database WHERE datname ~ '$(SCRATCH)'"); do \
	  echo "dropping $$name"; \
	  $(PSQL) -d postgres -c "DROP DATABASE $$name"; \
	done

clean:                  ## caches and build output (never data/)
	rm -rf .pytest_cache .ruff_cache build
