# Testing Conventions

We use `pytest` for all testing. Every new feature or bug fix must include associated tests.

## Structure

Tests are located in the `tests/` directory and should mirror the package structure:

- `tests/test_core_ir.py` -> `flowly/core/ir.py`
- `tests/test_engine_runner.py` -> `flowly/engine/runner.py`
- `tests/test_frontend_builder.py` -> `flowly/frontend/builder.py`

## Rules

1. **Type Annotations**: All test functions should be typed (where reasonable).
2. **Coverage**: Aim for high branch coverage.
3. **Naming**: Test functions should start with `test_` and describe the scenario (e.g., `test_decision_node_routing`).
4. **Fixtures**: Use pytest fixtures for common setup (e.g., creating a basic graph).

## Running Tests

```bash
pytest tests/
```
