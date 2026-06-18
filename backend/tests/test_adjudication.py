"""Unit tests for the core adjudication logic — the parts that must be provably correct:

  * `_alleges_fraud`     — the gate that decides whether Quinn (SIU) is recruited.
  * `_FRAUD_TRIGGERS`    — the trigger vocabulary.
  * `_payable`           — the deterministic payout (requested − deductible, clamped at zero).
  * `_transcript_hash`   — the SHA-256 tamper-evident audit fingerprint.
  * `_parse_resolution`  — parsing Sam's verdict into decision / amount / cited clauses.

These are pure functions, so the suite needs no database, no Band connection, and no network.
"""
import hashlib
from decimal import Decimal
from types import SimpleNamespace

import pytest

from services.orchestrator import (
    _FRAUD_TRIGGERS,
    _alleges_fraud,
    _parse_resolution,
    _payable,
    _transcript_hash,
)


def _claim(denial: str = "", incident: str = "") -> SimpleNamespace:
    """A minimal stand-in for a Claim — `_alleges_fraud` only reads these two text fields."""
    return SimpleNamespace(original_denial_reason=denial, incident_description=incident)


# --------------------------------------------------------------------------- #
# _alleges_fraud  — the SIU-recruitment gate (the dynamic-discovery trigger)
# --------------------------------------------------------------------------- #
class TestAllegesFraud:
    def test_lisa_park_commercial_use_denial_triggers(self):
        # Arrange: the seeded Lisa Park denial alleges undisclosed commercial/rideshare use.
        claim = _claim(
            denial="Claim denied per §7.4. Adjuster alleges undisclosed commercial (rideshare) use.",
            incident="Vehicle stereo and catalytic converter stolen overnight.",
        )
        # Act / Assert
        assert _alleges_fraud(claim) is True

    def test_david_chen_clean_collision_does_not_trigger(self):
        claim = _claim(
            denial="Claim denied — engine failure attributed to a pre-existing mechanical issue.",
            incident="Vehicle struck a guardrail on I-95; airbags deployed.",
        )
        assert _alleges_fraud(claim) is False

    def test_marcus_reyes_staged_loss_triggers(self):
        claim = _claim(
            denial="Denied per §7.4 — adjuster alleges a possible staged/intentional loss.",
            incident="The parked vehicle caught fire overnight and was a total loss.",
        )
        assert _alleges_fraud(claim) is True

    def test_empty_fields_do_not_trigger(self):
        assert _alleges_fraud(_claim()) is False

    def test_none_fields_do_not_trigger(self):
        assert _alleges_fraud(SimpleNamespace(original_denial_reason=None, incident_description=None)) is False

    def test_is_case_insensitive(self):
        assert _alleges_fraud(_claim(denial="ALLEGED FRAUD AND MISREPRESENTATION")) is True

    def test_trigger_in_incident_description_only(self):
        # The denial is clean but the incident text concedes a staged loss — still trips the gate.
        assert _alleges_fraud(_claim(denial="Denied.", incident="insured admits the loss was staged")) is True

    @pytest.mark.parametrize("trigger", _FRAUD_TRIGGERS)
    def test_every_trigger_word_fires(self, trigger):
        assert _alleges_fraud(_claim(denial=f"the adjuster cited {trigger} here")) is True

    def test_unrelated_text_does_not_fire(self):
        assert _alleges_fraud(_claim(denial="weather was clear; driver lost control on wet pavement")) is False


def test_fraud_triggers_are_nonempty_and_lowercase():
    assert len(_FRAUD_TRIGGERS) >= 5
    assert all(t == t.lower() for t in _FRAUD_TRIGGERS)
    assert "fraud" in _FRAUD_TRIGGERS and "misrepresent" in _FRAUD_TRIGGERS


# --------------------------------------------------------------------------- #
# _payable  — deterministic payout
# --------------------------------------------------------------------------- #
class TestPayable:
    def test_marcus_reyes_payout(self):
        assert _payable(Decimal("9800.00"), Decimal("500.00")) == Decimal("9300.00")

    def test_zero_deductible_pays_full_amount(self):
        assert _payable(Decimal("12000.00"), Decimal("0")) == Decimal("12000.00")

    def test_deductible_exceeding_amount_clamps_to_zero(self):
        assert _payable(Decimal("300.00"), Decimal("500.00")) == Decimal("0")

    def test_deductible_equal_to_amount_is_zero(self):
        assert _payable(Decimal("500.00"), Decimal("500.00")) == Decimal("0")

    def test_result_is_exact_decimal_not_float(self):
        result = _payable(Decimal("4200.00"), Decimal("500.00"))
        assert result == Decimal("3700.00")
        assert isinstance(result, Decimal)

    def test_never_negative(self):
        for amt, ded in [("0", "1000"), ("100.50", "100.51"), ("0", "0")]:
            assert _payable(Decimal(amt), Decimal(ded)) >= Decimal("0")


# --------------------------------------------------------------------------- #
# _transcript_hash  — tamper-evident SHA-256 fingerprint
# --------------------------------------------------------------------------- #
class TestTranscriptHash:
    PAIRS = [("coordinator", "case file"), ("blake", "argues for coverage"), ("sam", "APPROVED")]

    def test_matches_hand_computed_sha256(self):
        blob = "coordinator:case file\nblake:argues for coverage\nsam:APPROVED"
        expected = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        assert _transcript_hash(self.PAIRS) == expected

    def test_is_deterministic(self):
        assert _transcript_hash(self.PAIRS) == _transcript_hash(self.PAIRS)

    def test_is_64_hex_chars(self):
        h = _transcript_hash(self.PAIRS)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_tampering_with_content_changes_the_hash(self):
        tampered = [("coordinator", "case file"), ("blake", "argues for coverage"), ("sam", "DENIED")]
        assert _transcript_hash(self.PAIRS) != _transcript_hash(tampered)

    def test_reordering_changes_the_hash(self):
        reordered = list(reversed(self.PAIRS))
        assert _transcript_hash(self.PAIRS) != _transcript_hash(reordered)

    def test_empty_transcript_is_stable(self):
        assert _transcript_hash([]) == hashlib.sha256(b"").hexdigest()


# --------------------------------------------------------------------------- #
# _parse_resolution  — Sam's verdict -> structured fields
# --------------------------------------------------------------------------- #
class TestParseResolution:
    APPROVED = (
        "DECISION: APPROVED\nAPPROVED AMOUNT: $9,300.00\n"
        "LEGAL REASONING: covered under §5.2; §7.4 does not apply.\nCITED CLAUSES: §5.2 · §7.4"
    )

    def test_parses_approved_decision(self):
        assert _parse_resolution(self.APPROVED)["decision"] == "APPROVED"

    def test_parses_amount_with_commas_and_dollar_sign(self):
        assert _parse_resolution(self.APPROVED)["approved_amount"] == Decimal("9300.00")

    def test_extracts_unique_sorted_clauses(self):
        assert _parse_resolution(self.APPROVED)["cited_clauses"] == ["§5.2", "§7.4"]

    def test_denied_decision(self):
        assert _parse_resolution("DECISION: DENIED\nNo coverage under §3.1.")["decision"] == "DENIED"

    def test_partial_decision(self):
        assert _parse_resolution("DECISION: PARTIAL")["decision"] == "PARTIAL"

    def test_acknowledgment_text_is_unclear(self):
        # Sam sometimes acknowledges instead of ruling — must not be mistaken for a decision.
        assert _parse_resolution("Understood, I'll review the record and respond shortly.")["decision"] == "UNCLEAR"

    def test_handles_markdown_bold_around_decision(self):
        assert _parse_resolution("DECISION: **APPROVED**")["decision"] == "APPROVED"

    def test_no_amount_yields_none(self):
        assert _parse_resolution("DECISION: DENIED")["approved_amount"] is None

    def test_is_case_insensitive_for_decision(self):
        assert _parse_resolution("decision: approved")["decision"] == "APPROVED"
