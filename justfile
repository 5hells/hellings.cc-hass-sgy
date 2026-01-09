set shell := ["powershell", "-Command"]

test-default:
    python -m pytest tests

test *ARGS:
    python -m pytest tests/{{ARGS}}