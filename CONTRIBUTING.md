# Contributing

Thank you for helping improve the book's code. This repository is the
companion to *Retrieval Engineering*, so its first job is to match
what the book prints. That shapes what is welcome.

## Errata

If something in the book is wrong or unclear (a listing, a number, an
explanation), please open an issue with the **Errata** form. Give the
book, the chapter, the page or section and the edition (print, ebook
or web), what it says and what you expected. Confirmed errata are
fixed in the book and, where the code is involved, here.

## Bugs and pull requests

- **Bug fixes are welcome.** Open an issue with the **Bug report**
  form first, or a pull request that explains the bug and adds a test
  that fails without the fix.
- **Changes that would change a number the book prints** (a metric, a
  table, a default) start with an issue, so the book and the code stay
  in step.
- New features are usually out of scope: the code follows the book's
  chapters. Ideas for the book itself are welcome as issues.

## Style and checks

- Printed files stay within 76 characters a line: every `.py`, `.sql`,
  `.md`, `.toml` and `.yml` file and the Makefile, because the book
  prints them.
- Listings are cut from the code between `# region: <name>` and
  `# endregion: <name>` lines; keep those markers on their own lines
  and balanced.
- Keep the plain style: standard library and the pinned libraries in
  `requirements.lock`, no framework.

## Tests

```sh
make test         # every test; Postgres tests use RX_TEST_DSN
```

The tests must pass before a change is merged.
Tests that read the desk set or the generator's worlds skip when they
are not available; say in the pull request whether you ran them.

## License

By contributing, you agree that your contributions are licensed under
the Apache License 2.0, as the rest of the code is.

## Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
