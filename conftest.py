import pytest

from app.database.connection import SessionLocal
from app.ai.graph import build_supply_chain_graph


@pytest.fixture
def graph():
    """
    Build a fresh supply-chain graph from the database
    for each test.
    """

    session = SessionLocal()

    try:
        return build_supply_chain_graph(session)

    finally:
        session.close()