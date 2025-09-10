# Battery Notes Test Framework

## Running Tests

```bash
# Run all tests using the test script
./scripts/test

# Or run tests directly with pytest
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_init.py -v

# Run specific test
python -m pytest tests/test_init.py::TestBatteryNotesInit::test_async_setup_success -v

# Run with coverage
pytest --cov-report term-missing --cov=custom_components.battery_notes tests
```
