from datetime import date

import pytest

from complymate.domain.risk.engine import RuleError, evaluate, next_review_date, score
from complymate.domain.risk.factors import ClientFacts, PartyFacts
from complymate.domain.risk.rules_loader import load_rules

RULES = load_rules("AU")


def facts(**kw):
    base = ClientFacts(
        client_type="individual", residential_country="AU", nationality="AU", source_of_funds_verified=True
    )
    for k, v in kw.items():
        setattr(base, k, v)
    return base.to_facts("AU")


def test_plain_local_individual_is_low():
    result = score(facts(), RULES)
    assert result.level == "low"
    assert result.score == 0
    assert result.rules_version == RULES.version


def test_pep_is_always_high_with_reason():
    result = score(facts(is_pep=True), RULES)
    assert result.level == "high"
    assert result.auto_high
    assert result.reasons[0].factor_id == "customer.pep"


def test_pep_beneficial_owner_counts():
    result = score(
        facts(client_type="company", parties=[PartyFacts(is_pep=True, ownership_percent=40, verified=True)]), RULES
    )
    assert result.level == "high"


def test_fatf_call_for_action_country_forces_high():
    result = score(facts(nationality="KP"), RULES)
    assert result.level == "high"
    assert any(r.factor_id == "geography.fatf_call_for_action" for r in result.reasons)


def test_medium_from_combined_factors():
    result = score(
        facts(channel="non_face_to_face", services=["handling_client_money"], residential_country="NZ"), RULES
    )
    # 4 (non f2f) + 5 (higher-risk service) + 3 (foreign) = 12
    assert result.score == 12
    assert result.level == "medium"


def test_company_with_unverified_owners_and_layers():
    result = score(
        facts(
            client_type="company",
            residential_country=None,
            country_of_incorporation="AU",
            parties=[PartyFacts(ownership_percent=30, depth=3, verified=False)],
        ),
        RULES,
    )
    ids = {r.factor_id for r in result.reasons}
    assert {"customer.complex_structure", "customer.unidentified_beneficial_owner"} <= ids


def test_deterministic():
    f = facts(channel="intermediary", cash_intensive=True)
    assert score(f, RULES).as_dict() == score(f, RULES).as_dict()


def test_true_match_is_high():
    assert score(facts(screening_true_match=True), RULES).level == "high"


def test_unknown_operator_raises():
    with pytest.raises(RuleError):
        evaluate({"fact": "x", "op": "nope"}, {"x": 1}, RULES)


@pytest.mark.parametrize(
    ("level", "expected"), [("low", date(2029, 1, 31)), ("medium", date(2028, 1, 31)), ("high", date(2027, 1, 31))]
)
def test_review_periods(level, expected):
    assert next_review_date(level, RULES, date(2026, 1, 31)) == expected


def test_review_date_month_end_clamps():
    rules = load_rules("AU")
    assert next_review_date("high", rules, date(2027, 2, 28)) == date(2028, 2, 28)


def test_nz_rules_load():
    nz = load_rules("NZ")
    assert nz.jurisdiction == "NZ" and nz.home_country == "NZ"
