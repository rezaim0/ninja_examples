import pandas as pd
import pytest

from your_module import (
    apply_log_rule,
    apply_fallback_rule,
    determine_emails_to_send,
)


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def make_output_df(rows):
    """
    rows: list of tuples (model_name, days_due)
    """
    return pd.DataFrame(rows, columns=["model_name", "days_due"])


def make_log_df(rows):
    """
    rows: list of tuples (model_name, timestamp)
    """
    return pd.DataFrame(rows, columns=["model_name", "email_json_generated_at"])


# -------------------------------------------------
# Unit Tests — Log Rule
# -------------------------------------------------

def test_log_rule_blocks_recent_email():
    df = make_output_df([("A", 20)])

    recent_time = pd.Timestamp.now() - pd.Timedelta(days=3)
    log = make_log_df([("A", recent_time)])

    result = apply_log_rule(df, log, days_threshold=15)

    assert result.loc[0, "send_email"] is False


def test_log_rule_allows_old_email():
    df = make_output_df([("A", 1)])

    old_time = pd.Timestamp.now() - pd.Timedelta(days=20)
    log = make_log_df([("A", old_time)])

    result = apply_log_rule(df, log, days_threshold=15)

    assert result.loc[0, "send_email"] is True


# -------------------------------------------------
# Unit Tests — Fallback Rule
# -------------------------------------------------

def test_fallback_first_overdue_kickoff():
    df = make_output_df([("A", 5)])
    df["send_email"] = pd.NA

    result = apply_fallback_rule(df)

    assert result.loc[0, "send_email"] is True


def test_fallback_not_overdue_no_window():
    df = make_output_df([("A", -5)])
    df["send_email"] = pd.NA

    result = apply_fallback_rule(df)

    # Should remain NA → filtered later
    assert pd.isna(result.loc[0, "send_email"])


def test_fallback_recurring_14_day_rule():
    df = make_output_df([("A", 16)])  # 2 + 14
    df["send_email"] = pd.NA

    result = apply_fallback_rule(df)

    assert result.loc[0, "send_email"] is True


# -------------------------------------------------
# Integration Test — Priority & Layering
# -------------------------------------------------

def test_determine_emails_to_send_integration():
    now = pd.Timestamp.now()

    output_df = pd.DataFrame(
        [
            ("A", 20),   # Has recent log → blocked
            ("B", 5),    # No log → kickoff
            ("C", -10),  # No log → no send
            ("D", 16),   # No log → recurring rule
        ],
        columns=["model_name", "days_due"],
    )

    log_df = pd.DataFrame(
        [
            ("A", now - pd.Timedelta(days=3)),  # recent email
        ],
        columns=["model_name", "email_json_generated_at"],
    )

    result = determine_emails_to_send(output_df, log_df)

    models_sent = set(result["model_name"])

    assert models_sent == {"B", "D"}