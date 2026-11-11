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
	$(PYTHON) -m pip install -e .

clean:                  ## caches and build output (never data/)
	rm -rf .pytest_cache .ruff_cache build
