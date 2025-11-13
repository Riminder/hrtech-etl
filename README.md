# HrTech ETL (wip)
Opensource ETL framework for HRTech data (jobs & profiles) across ATS, CRM, Jobboard, and HCM systems.

## Repository Structure

```bash
hrtech-etl/
├─ pyproject.toml
├─ README.md
├─ src/
│  └─ hrtech_etl/
│     ├─ __init__.py
│     ├─ core/
│     │  ├─ __init__.py
│     │  ├─ types.py
│     │  ├─ models.py
│     │  ├─ auth.py
│     │  └─ pipeline.py
│     └─ connectors/
│        ├─ __init__.py
│        ├─ base.py
│        ├─ warehouse_a/
│        │  ├─ __init__.py
│        │  ├─ models.py
│        │  └─ client.py
│        └─ warehouse_b/
│           ├─ __init__.py
│           ├─ models.py
│           └─ client.py
└─ tests/
   ├─ test_pipeline.py
   └─ test_connectors.py
```