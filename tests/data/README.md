# Test Data

This directory contains small, sanitized Sleeper API samples used for local tests.

Raw league captures are kept under `tests/private/` and are ignored by git.

Committed samples should:

- replace manager names, usernames, avatars, and user IDs
- keep only the weeks needed for tests
- trim large stat responses
- preserve enough Sleeper response shape to test parsing and domain logic
