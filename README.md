# Retrieval Engineering: companion code

[![License: Apache-2.0][license-badge]](LICENSE)
[![Python 3.13][python-badge]](https://www.python.org/)

The code for *Retrieval Engineering: Production RAG, from Millions of
Messy Documents to Cited Answers* by Ahsan Iqbal (forthcoming). Every
listing in the book is cut from these files, and every number the book
prints comes from running them on the book's dataset.

It is plain Python and PostgreSQL, with no framework: you can read
every step that turns a pile of documents into a cited answer, run
it, measure it and change it. It is written for engineers who build
or run retrieval systems and for computer science students who want to
learn retrieval from the ground up.

The repository grows chapter by chapter as the book is finalized; the
[changelog](CHANGELOG.md) lists what is here so far.

## Setup without Docker

You need Python 3.12 or newer (the book uses 3.13) and PostgreSQL 15
or newer with pgvector 0.8 or newer.

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock      # the versions the book used
pip install --no-deps -e .            # this package
export RX_DSN=postgresql://postgres@localhost:5432/rx
export RX_TEST_DSN=postgresql://postgres@localhost:5432/rx_test
make db                               # create rx and rx_test
```

## Repository layout

```
rx/              the package: one module per idea
sql/             schema files, applied in name order
tests/           pytest suite; tests marked `db` need Postgres
requirements.lock  the exact library versions the book used
```

Run every command from the repository root.

## Running the tests

```sh
make test-fast    # fast tests: no database, no generator runs
make test         # every test; Postgres tests use RX_TEST_DSN
```

The test database is reset by the tests: never point `RX_TEST_DSN` at
a database you want to keep.

## Errata and issues

Found a mistake in the book or a bug in the code? Please open an
issue: there are forms for [errata][new-issue] (with the chapter and
page), bugs and questions.

## Contributing

Bug fixes are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). The
code follows the book, so changes that would change a printed number
start with an issue. This project follows the
[Contributor Covenant](CODE_OF_CONDUCT.md).

## License

The code is licensed under the [Apache License 2.0](LICENSE).

[license-badge]: https://img.shields.io/badge/license-Apache--2.0-blue
[python-badge]: https://img.shields.io/badge/python-3.13-blue
[new-issue]: ../../issues/new/choose
