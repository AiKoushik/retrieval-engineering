-- The two databases the book uses; `make index` fills rx, the tests use
-- rx_test. Lab commands create their own scratch databases (rx_ch06, ...).
CREATE DATABASE rx;
CREATE DATABASE rx_test;
\c rx
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_textsearch;
\c rx_test
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_textsearch;
