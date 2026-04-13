from __future__ import annotations

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.build_mt4_html_report import recompute_candidate_metrics_from_journal


@pytest.fixture
def journals_by_fam() -> dict[str, list[dict[str, float]]]:
    return {
        "FAM_0001": [
            {"net_pnl": 100.0},
            {"net_pnl": -30.0},
            {"net_pnl": 50.0},
        ],
        "FAM_0002": [
            {"net_pnl": 20.0},
            {"net_pnl": 10.0},
            {"net_pnl": -5.0},
            {"net_pnl": 5.0},
        ],
    }


def test_section6_total_trades_equals_journal_count(journals_by_fam: dict[str, list[dict[str, float]]]) -> None:
    for family_id, journal in journals_by_fam.items():
        row = recompute_candidate_metrics_from_journal(family_id, journals_by_fam, start_capital=10_000.0)
        assert row["total_trades"] == len(journal)


def test_section6_win_rate_equals_journal_truth(journals_by_fam: dict[str, list[dict[str, float]]]) -> None:
    for family_id, journal in journals_by_fam.items():
        row = recompute_candidate_metrics_from_journal(family_id, journals_by_fam, start_capital=10_000.0)
        wins = sum(1 for trade in journal if trade["net_pnl"] > 0)
        expected_win_rate = wins / len(journal) * 100.0
        assert row["win_rate_pct"] == pytest.approx(expected_win_rate)


def test_section6_return_pct_uses_pnl_over_starting_capital(journals_by_fam: dict[str, list[dict[str, float]]]) -> None:
    start_capital = 10_000.0
    for family_id, journal in journals_by_fam.items():
        row = recompute_candidate_metrics_from_journal(family_id, journals_by_fam, start_capital=start_capital)
        expected_pnl = sum(trade["net_pnl"] for trade in journal)
        expected_return_pct = expected_pnl / start_capital * 100.0
        assert row["return_pct"] == pytest.approx(expected_return_pct)


def test_section6_no_default_zero_win_rate_for_profitable_candidate() -> None:
    journals = {
        "FAM_0009": [
            {"net_pnl": 30.0},
            {"net_pnl": 25.0},
            {"net_pnl": -10.0},
        ]
    }
    row = recompute_candidate_metrics_from_journal("FAM_0009", journals, start_capital=10_000.0)
    assert row["total_net_profit"] > 0
    assert row["win_rate_pct"] > 0.0


def test_section6_missing_journal_fails_loudly() -> None:
    with pytest.raises(FileNotFoundError):
        recompute_candidate_metrics_from_journal("FAM_404", {}, start_capital=10_000.0)
