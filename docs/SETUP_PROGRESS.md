ReRoute — Development Progress Documentation

1. Project Overview

Project: ReRoute
Title: Intelligent Supply-Chain Disruption Planner
Type: Classical-AI Decision-Support System for Supply-Chain Recovery Planning

ReRoute is being developed as a two-person project. The system will eventually model a supply chain as a graph, simulate disruptions, generate recovery plans using classical AI techniques such as A* search and CSP, evaluate risk and cost, rank feasible plans, and expose the results through a FastAPI backend and React frontend.

2. Repository Architecture

The project has been intentionally split into two separate GitHub repositories.

ReRoute
│
├── ReRoute_Backend
│
└── ReRoute_Frontend

ReRoute_Backend

Planned responsibilities:

FastAPI REST API

PostgreSQL database integration

SQLAlchemy models

Supply-chain data generation

Graph/AI engine

A* search

CSP validation

Bayesian risk calculation

Cost and plan scoring

Evaluation scripts

Docker/deployment configuration

ReRoute_Frontend

Planned responsibilities:

React application

TypeScript

Vite

Tailwind CSS

Supply-chain graph visualization

Disruption controls

Recovery-plan results

Charts and UI

The frontend and backend will communicate through a REST API.

3. Current Development Status

Completed

Decided to use two separate repositories

Created/started ReRoute_Backend

Created/started ReRoute_Frontend

Opened the project in VS Code

Created Python virtual environment for backend

Installed initial backend dependencies

Generated requirements.txt

Created backend folder structure

Created FastAPI application

Started FastAPI successfully

Verified root API endpoint

Verified /health endpoint through Swagger

Confirmed HTTP 200 response from /health

Not Yet Started

Neon PostgreSQL setup

Database schema

SQLAlchemy database models

Synthetic supply-chain data

NetworkX graph implementation

Disruption simulator

A* implementation

CSP implementation

Risk model

Cost/scoring engine

Complete REST API

React dashboard

Frontend-backend integration

Evaluation experiments

Docker setup

Deployment

Final documentation/report

4. Backend Environment

Python Environment

A virtual environment was created inside the backend repository:

ReRoute_Backend/
└── venv/

The active interpreter is:

ReRoute_Backend/venv/Scripts/python.exe

Python version currently being used:

Python 3.13.14

The global Python installation remains separate and is not being used for the project dependencies.

5. Backend Dependencies Installed

The initial backend environment contains:

FastAPI
Uvicorn
SQLAlchemy
psycopg2-binary
NetworkX
NumPy
SciPy
Pytest

Dependencies were frozen into:

requirements.txt

These packages cover the initial requirements for:

REST API development

PostgreSQL connectivity

ORM/database modelling

Graph representation

Numerical/synthetic data generation

Testing

Additional packages may be added later when required by the implementation.

6. Backend Folder Structure

The current backend structure is:

ReRoute_Backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── ai/
│   │   └── __init__.py
│   │
│   ├── api/
│   │   └── __init__.py
│   │
│   ├── database/
│   │   └── __init__.py
│   │
│   ├── models/
│   │   └── __init__.py
│   │
│   └── schemas/
│       └── __init__.py
│
├── scripts/
├── tests/
├── venv/
├── .gitignore
├── README.md
└── requirements.txt

Purpose of the directories

Directory

Purpose

app/

Main backend application

app/api/

FastAPI routes/endpoints

app/models/

Database models

app/schemas/

API request/response schemas

app/ai/

Classical-AI implementation

app/database/

Database connection/configuration

scripts/

Data generation and evaluation scripts

tests/

Automated tests

venv/

Backend Python virtual environment

7. FastAPI Application

The first FastAPI application has been created in:

app/main.py

Current endpoints:

GET /
GET /health

The application is configured with:

Title:
ReRoute API

Description:
Intelligent Supply-Chain Disruption Planner

Version:
1.0.0

8. Current FastAPI Code

The current application contains the following functionality:

from fastapi import FastAPI

app = FastAPI(
    title="ReRoute API",
    description="Intelligent Supply-Chain Disruption Planner",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "ReRoute API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

9. Backend Verification

The FastAPI server was successfully started using:

uvicorn app.main:app --reload

Local backend address:

http://127.0.0.1:8000

Root Endpoint

Request:

GET /

Successful response:

{
  "message": "ReRoute API is running"
}

Health Endpoint

Request:

GET /health

Successful response:

{
  "status": "healthy"
}

HTTP status:

200 OK

Swagger Documentation

FastAPI's interactive documentation was successfully accessed at:

http://127.0.0.1:8000/docs

The /health endpoint was executed through Swagger and returned HTTP 200.

10. Expected System Architecture

The final system is planned to follow:

                    USER
                      │
                      ▼
          ┌──────────────────────┐
          │  ReRoute Frontend    │
          │ React + TypeScript   │
          │ Vite + Tailwind      │
          └──────────┬───────────┘
                     │
                     │ REST API
                     ▼
          ┌──────────────────────┐
          │   ReRoute Backend    │
          │ FastAPI + AI Engine  │
          └──────────┬───────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
       PostgreSQL       Classical AI
                         Engine
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
             A*            CSP       Risk/Scoring
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                  Ranked Recovery Plans
                            │
                            ▼
                       Frontend UI

11. Planned API Contract

The initial API contract has been defined conceptually.

Simulate Disruption

POST /disruptions/simulate

Request example:

{
  "disruption_type": "supplier_failure",
  "target_id": "SUP-001",
  "magnitude": 1.0,
  "duration": 7
}

Recommend Plans

GET /plans/recommend?scenario_id=SCN-001

Expected response structure:

{
  "scenario_id": "SCN-001",
  "plans": [
    {
      "rank": 1,
      "cost": 12500,
      "delay": 2,
      "risk": 0.12,
      "actions": [],
      "explanation": "..."
    }
  ]
}

This contract will be refined when the actual database and AI pipeline are implemented.

12. Next Development Phase

The immediate next phase is PostgreSQL + Neon setup.

The planned initial database entities are:

suppliers
warehouses
factories
customers
routes
orders

After the database foundation, development will proceed in this order:

PostgreSQL
    ↓
SQLAlchemy Models
    ↓
Synthetic Data
    ↓
NetworkX Graph
    ↓
Disruption Simulator
    ↓
A* Search
    ↓
CSP Validation
    ↓
Risk Calculation
    ↓
Cost + Scoring
    ↓
FastAPI Integration
    ↓
React Dashboard
    ↓
Evaluation
    ↓
Deployment

13. Current Git Checkpoint

This documentation should be committed together with the completed backend foundation.

Recommended commit:

Set up initial ReRoute backend

The next development work should happen in a feature branch rather than directly on main.

Recommended branch naming:

feature/database-schema

14. Development Rules

Keep main in a working state.

Use feature branches for new development.

Open a Pull Request before merging.

Commit small, meaningful changes.

Keep the API contract synchronized between frontend and backend.

Do not let frontend and backend implementations diverge from the agreed API.

Integrate frequently.

Test each major component before moving forward.

Keep secrets and database credentials out of Git.

Prioritize the core Classical-AI functionality before UI polishing.

15. Current Milestone

Milestone 1 — Backend Foundation

Status: COMPLETE

Repository
     ✓
Python Environment
     ✓
Dependencies
     ✓
Folder Structure
     ✓
FastAPI
     ✓
Root Endpoint
     ✓
Health Endpoint
     ✓
Swagger Verification
     ✓

Next milestone:

Milestone 2 — Database Foundation

This will begin with Neon PostgreSQL and the ReRoute supply-chain schema.