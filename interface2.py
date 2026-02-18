from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

import pandas as pd


# ============================================================
# Base Strategy
# ============================================================

class NotificationStrategy(ABC):
    """
    Contract for all notification strategies.

    Each strategy must:
    - Apply log-based rule
    - Apply fallback scheduling rule
    """

    @abstractmethod
    def apply_log_rule(
        self,
        df: pd.DataFrame,
        log_df: pd.DataFrame,
        *,
        now: pd.Timestamp,
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    def apply_fallback_rule(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        pass


# ============================================================
# Concrete Strategy: Model Review Notification
# ============================================================

class ModelReviewNotification(NotificationStrategy):

    DAYS_THRESHOLD = 15
    NOTIFICATION_TYPE = "model_review"

    def apply_log_rule(
        self,
        df: pd.DataFrame,
        log_df: pd.DataFrame,
        *,
        now: pd.Timestamp,
    ) -> pd.DataFrame:
        """
        Contract:
        - df must contain: model_name
        - log_df must contain: model_name, notification_type, email_json_generated_at
        - returns df + nullable boolean column send_notification
        """

        if "model_name" not in df.columns:
            raise ValueError("Missing required column: model_name")

        required_log_cols = {
            "model_name",
            "notification_type",
            "email_json_generated_at",
        }
        if not required_log_cols.issubset(log_df.columns):
            raise ValueError(
                f"log_df missing required columns: {required_log_cols}"
            )

        log_df = log_df.copy()

        # Filter to only this notification type
        log_df = log_df[
            log_df["notification_type"] == self.NOTIFICATION_TYPE
        ]

        log_df["email_json_generated_at"] = pd.to_datetime(
            log_df["email_json_generated_at"],
            errors="coerce",
        )

        merged = df.merge(
            log_df[["model_name", "email_json_generated_at"]],
            on="model_name",
            how="left",
        )

        has_log = merged["email_json_generated_at"].notna()
        is_old = (
            now - merged["email_json_generated_at"]
        ) >= pd.Timedelta(days=self.DAYS_THRESHOLD)

        merged["send_notification"] = pd.Series(
            pd.NA,
            index=merged.index,
            dtype="boolean",
        )

        merged.loc[has_log & is_old, "send_notification"] = True
        merged.loc[has_log & ~is_old, "send_notification"] = False

        return merged

    def apply_fallback_rule(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Contract:
        - df must contain: days_due
        - df must contain: send_notification (nullable boolean)
        """

        if "days_due" not in df.columns:
            raise ValueError("Missing required column: days_due")

        if "send_notification" not in df.columns:
            raise ValueError("Missing required column: send_notification")

        out = df.copy()

        fallback_mask = out["send_notification"].isna()

        if not fallback_mask.any():
            return out

        d = out.loc[fallback_mask, "days_due"]

        # ----------------------------------------------------
        # First-ever overdue → immediate send
        # ----------------------------------------------------
        kickoff_mask = d > 0
        out.loc[fallback_mask & kickoff_mask, "send_notification"] = True

        # ----------------------------------------------------
        # Recurring scheduling windows
        # ----------------------------------------------------
        fallback_mask = out["send_notification"].isna()
        d = out.loc[fallback_mask, "days_due"]

        trigger_mask = (
            d.between(-31, -29)   # 1 month before
            | d.between(-14, -12) # 2 weeks before
            | d.between(0, 2)     # just overdue
            | ((d >= 2) & ((d - 2) % 14 == 0))  # every 14 days
        )

        out.loc[fallback_mask & trigger_mask, "send_notification"] = True

        return out


# ============================================================
# Strategy Registry
# ============================================================

STRATEGIES: Dict[str, NotificationStrategy] = {
    "model_review": ModelReviewNotification(),
}


# ============================================================
# Orchestrator
# ============================================================

def determine_notifications_to_send(
    output_df: pd.DataFrame,
    log_df: pd.DataFrame,
    notification_type: str,
    *,
    now: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Main entry point.

    Contract:
    - output_df must contain:
        model_name
        days_due
    - log_df must contain:
        model_name
        notification_type
        email_json_generated_at
    """

    if now is None:
        now = pd.Timestamp.now()

    if "model_name" not in output_df.columns:
        raise ValueError("output_df missing 'model_name' column")

    if "days_due" not in output_df.columns:
        raise ValueError("output_df missing 'days_due' column")

    strategy = STRATEGIES.get(notification_type)

    if strategy is None:
        raise ValueError(
            f"Unknown notification_type: {notification_type}"
        )

    df = output_df.copy()

    # 1. Apply log rule
    df = strategy.apply_log_rule(df, log_df, now=now)

    # 2. Apply fallback rule
    df = strategy.apply_fallback_rule(df)

    # 3. Return only rows to send
    return df[df["send_notification"] == True].copy()