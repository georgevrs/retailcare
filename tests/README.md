# RetailCare Test Suite

This directory contains comprehensive unit tests for all RetailCare functionality.

## Running Tests

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_intent_classification.py
```

### Run with Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

## Test Files

- **test_intent_classification.py** - Tests for intent classification logic
- **test_slot_extraction.py** - Tests for slot extraction from user input
- **test_policy_check.py** - Tests for policy engine (refund, cancellation policies)
- **test_store_info.py** - Tests for store hours and information
- **test_faq.py** - Tests for FAQ knowledge base search
- **test_state.py** - Tests for session state management
- **test_dialogue_flow.py** - Tests for dialogue flow and next question generation
- **test_github_issues.py** - Tests for GitHub Issues integration
- **test_playbooks.py** - Tests for automation playbooks
- **test_remediation_worker.py** - Tests for remediation worker
- **test_confirmation_messages.py** - Tests for confirmation message generation
- **test_text_cleaning.py** - Tests for text cleaning for TTS

## Test Structure

Each test file follows pytest conventions:
- Test classes group related tests
- Fixtures provide test data and mocks
- Async tests use `@pytest.mark.asyncio`

## Mocking

Tests use `unittest.mock` and `pytest-mock` for:
- External API calls (GitHub, OpenAI)
- File system operations
- Network requests

## Golden Tests

See `golden_conversations/` for end-to-end conversation test scenarios.
