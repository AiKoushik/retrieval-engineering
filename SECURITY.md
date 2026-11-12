# Security policy

## Supported versions

Fixes go into the `main` branch and the latest release.

## Reporting a vulnerability

Please don't open a public issue for a security problem. Use GitHub's
private vulnerability reporting (the **Security** tab, then **Report a
vulnerability**). If that is not available, contact the maintainer
via GitHub (<https://github.com/AiKoushik>) and ask for a private
channel. Reports are answered as soon as possible.

## Scope and safe use

- The code is meant for learning and experiments on your own machine.
  The Docker database uses passwordless `trust` authentication for
  convenience: never expose its port beyond your machine.
- The tests reset the database named by `RX_TEST_DSN`. Point it at a
  throwaway database, never at data you want to keep.
- The Tarnwick dataset contains one labeled, planted instruction (an
  email that hides text aimed at AI assistants). It is there on
  purpose, so the book can show that retrieved text is data and never
  instructions; it is not a vulnerability.
