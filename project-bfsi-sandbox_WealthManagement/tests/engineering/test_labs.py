"""Labs: observable business outcomes and their protections."""

import importlib

import pytest

from chronos.api_schemas_requests_and_responses import TradeRequest
from chronos.business_investor_trading import execute_investor_trade
from labs.registry import LABS, visible_labs_for_role


def test_all_m1_to_m15_lab_starters_are_registered():
    assert [lab.module_number for lab in LABS] == list(range(1, 16))

    for lab in LABS:
        starter = importlib.import_module(lab.starter_module)
        assert callable(starter.render)
        assert callable(starter.run)
        with pytest.raises(NotImplementedError):
            starter.run({"role": lab.roles[0]}, "starter input")


def test_each_demo_role_sees_relevant_lab_pages():
    assert any(lab.module_number == 1 for lab in visible_labs_for_role("INVESTOR"))
    assert any(lab.module_number == 7 for lab in visible_labs_for_role("ADVISOR"))


def test_m12_starter_reads_bounded_current_portfolio(db, alice, alice_account):
    from labs.m12_governed_mcp.server import read_bounded_portfolio

    execute_investor_trade(
        db,
        alice_account,
        TradeRequest(user_id=alice.id, symbol="AAPL", side="BUY", amount=10_800.0),
    )
    db.commit()

    result = read_bounded_portfolio("alice@example.com", max_positions=1)

    assert result["source"] == "chronos_portfolio_snapshot"
    assert result["simulated_date"] == "2020-06-01"
    assert result["holdings"] == [{"symbol": "AAPL", "shares": 100.0}]


def test_m12_host_admission_excludes_unapproved_tools_before_dispatch():
    from labs.m12_governed_mcp.host_admission import admission_denial, admitted_tools

    discovered = {"advisor_client_portfolio", "export_all_holdings"}

    assert admitted_tools(discovered) == []
    assert admission_denial("export_all_holdings") == {
        "status": "not_implemented",
        "reason": "host_admission_not_implemented",
    }
    assert admission_denial("advisor_client_portfolio") == {
        "status": "not_implemented",
        "reason": "host_admission_not_implemented",
    }
