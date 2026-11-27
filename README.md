# AI Quality Engineering Platform

An AI-powered Quality Engineering platform demonstrating modern software testing practices through Generative AI, Agentic AI, BDD, API automation, and browser automation.

## Project Vision

Build an intelligent Quality Engineering platform that converts natural-language requirements into traditional test cases and BDD scenarios, supports automated test execution, evaluates AI-generated responses, analyses automation failures, and provides actionable quality insights.

The platform aims to demonstrate how AI can enhance the complete Software Testing Life Cycle (STLC), from requirement analysis and test design to execution and reporting.

## Business Domain

**Banking and Payment Systems**

The platform uses a simulated payment application with synthetic test data to demonstrate:

- Payment transaction validation
- Duplicate transaction detection
- Idempotency validation
- API security testing
- Sensitive data masking
- Positive and negative testing
- Boundary-value testing
- Payment authorization and validation

No real customer, banking, or payment information will be used.

### Payment Simulation Rules

- Payment outcomes are deterministic. Amounts of `100000` or more receive a
  simulated `FAILED` status; this fixed threshold is a demo trigger, not a
  banking or payment-network limit.
- Simulated SWIFT requests must be cross-border and include a supported
  destination currency. Matching source and destination currencies do not
  invoke FX conversion; different supported currencies use the FX reference
  rate service. SWIFT is represented only as a simulation label; no real
  payment messaging or settlement occurs.
- FX rates are rounded half-up to eight decimal places, matching the database
  precision (`Numeric(18, 8)`). Converted amounts use `Decimal` and are rounded
  half-up to two decimal places.

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3.12 |
| AI Model | OpenAI API |
| Frontend | Streamlit |
| Backend | FastAPI |
| UI Automation | Playwright |
| API Automation | Pytest + Requests |
| BDD Framework | Gherkin + pytest-bdd (planned) |
| Data Validation | Pydantic |
| Database | SQLite |
| ORM | SQLAlchemy |
| Reporting | Allure |
| CI/CD | GitHub Actions |
| Version Control | Git + GitHub |

## Platform Modules

| Module | Description | Status |
|---|---|---|
| AI Test Case Generator | Generate traditional test cases from natural-language requirements | Planned |
| AI BDD Scenario Generator | Generate Gherkin scenarios using Given–When–Then | Planned |
| Test Case to BDD Converter | Convert traditional test cases into BDD scenarios | Planned |
| BDD Quality Validator | Validate Gherkin structure, steps, and scenario quality | Planned |
| API Automation | Generate and execute payment API test scenarios | Planned |
| Agentic AI Testing | Use AI-assisted planning to execute browser tests with Playwright | Planned |
| AI Failure Analysis | Analyse logs, screenshots, and DOM evidence to suggest root causes | Planned |
| LLM Evaluation | Evaluate AI response accuracy, consistency, hallucination, and latency | Planned |
| QE Dashboard | Display execution metrics and quality insights | Planned |

## Test Design Capabilities

The AI-powered test design modules will support:

- Positive test scenarios
- Negative test scenarios
- Boundary-value analysis
- Equivalence partitioning
- Data-driven test scenarios
- API validation scenarios
- Security and data-masking scenarios
- Banking and payment-specific validations

### BDD Scenario Generation

The platform will generate Gherkin feature files using:

- Feature
- Background (where applicable)
- Scenario
- Scenario Outline
- Examples
- Given–When–Then steps

The preferred structure is positive scenarios first, followed by negative and boundary scenarios.

### Example BDD Scenario

```gherkin
Feature: Fund Transfer

  Scenario: Successful fund transfer
    Given the customer has a valid bank account
    And the account has sufficient balance
    When the customer transfers money to a valid beneficiary
    Then the transaction should be successful
    And the account balance should be updated

  Scenario: Prevent duplicate transactions
    Given the customer has initiated a fund transfer
    When the same transaction request is submitted again
    Then the duplicate transaction should be prevented
```

## Project Architecture

```text
                    User
                      |
                      v
              Streamlit Dashboard
                      |
                      v
                 FastAPI Backend
                      |
              +-------+-------+
              |               |
              v               v
           AI Engine     Test Generation
           (OpenAI)           |
                     +--------+---------+
                     |        |         |
                     v        v         v
                 Test Cases  BDD     Test Case
                            Scenarios  to BDD
                     |        |         |
                     +--------+---------+
                              |
                              v
                       Test Execution
                              |
                 +------------+------------+
                 |            |            |
                 v            v            v
              API Tests    UI Tests    BDD Tests
              (Pytest)   (Playwright) (pytest-bdd)
                 |            |            |
                 +------------+------------+
                              |
                              v
                       SQLite Database
                              |
                              v
                        Allure Reports
                              |
                              v
                         QE Dashboard
```

## Project Structure

```text
ai-quality-engineering-platform/
|
|-- .github/
|   |-- workflows/
|
|-- ai_engine/
|   |-- Test generation and AI integration
|
|-- automation/
|   |-- agents/
|   |-- api/
|   |-- ui/
|
|-- backend/
|   |-- api/
|   |-- models/
|   |-- services/
|
|-- docs/
|
|-- frontend/
|   |-- pages/
|
|-- mock_payment_service/
|
|-- reports/
|
|-- test_data/
|
|-- tests/                 (planned)
|   |-- unit/
|   |-- integration/
|   |-- api/
|   |-- ui/
|   |-- bdd/
|       |-- features/
|
|-- .gitignore
|-- README.md
|-- requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.12
- Git
- Visual Studio Code
- OpenAI API key (required for AI-powered functionality)

### Clone the Repository

```bash
git clone https://github.com/prado555/ai-quality-engineering-platform.git
cd ai-quality-engineering-platform
```

### Create and Activate Virtual Environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### Install Playwright Chromium

```powershell
python -m playwright install chromium
```

Application startup instructions will be added after the backend and frontend implementations are completed.

## Security

- API keys will be stored in environment variables.
- `.env` files will be excluded from Git.
- Synthetic payment data will be used.
- Sensitive configuration files will not be committed.
- Security testing will include PCI DSS-inspired validation scenarios.
- No real payment credentials or customer information will be stored.

## Development Status

**Current phase:** Initial project setup completed; application development pending.

The Python environment, project dependencies, core imports, and Playwright Chromium browser launch have been verified.

All platform modules remain planned until their implementations and tests are completed successfully.

## Author

**Prasad Antarkar**

Staff Engineer | SDET | AI Quality Engineering | Test Automation | Agentic AI