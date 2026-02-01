from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict

import pandas as pd


# ============================================================================
# DOMAIN MODEL
# ============================================================================

@dataclass(frozen=True)
class EmailFile:
    aap_group_id: str
    subject: str
    environment: str
    body: str
    model_name: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "aap_group_id": self.aap_group_id,
            "subject": self.subject,
            "environment": self.environment,
            "body": self.body,
        }


# ============================================================================
# PRESENTATION / RENDERING
# ============================================================================

def generate_model_review_html(
    model_name: str,
    model_repo: str,
    review_date: str,
    days_due: str,
) -> str:
    return f"""
    <html>
      <body>
        <h2>Model Review Required</h2>
        <p><strong>Model:</strong> {model_name}</p>
        <p><strong>Repository:</strong> {model_repo}</p>
        <p><strong>Review Date:</strong> {review_date}</p>
        <p><strong>Days Due:</strong> {days_due}</p>
      </body>
    </html>
    """


# ============================================================================
# UTILITIES
# ============================================================================

def sanitise_json_file_name(aap_group_id: str, model_name: str) -> str:
    clean_aap_id = re.sub(r"[^\w\-]", "_", str(aap_group_id))
    clean_model_name = re.sub(r"[^\w\-]", "_", str(model_name))
    return f"{clean_aap_id}_{clean_model_name}.json"


# ============================================================================
# CORE TRANSFORMATION LOGIC
# ============================================================================

HtmlRenderer = Callable[..., str]

def create_email_data(
    row: pd.Series,
    column_mapping: Dict[str, str],
    html_renderer: HtmlRenderer,
) -> EmailFile:
    model_name = str(row[column_mapping["model_name"]])
    model_repo = str(row[column_mapping["repo_link"]])
    review_date = str(row[column_mapping["review_date"]])
    days_due = str(row[column_mapping["days_due"]])
    aap_group_id = str(row[column_mapping["aap_group_id"]])

    body = html_renderer(
        model_name=model_name,
        model_repo=model_repo,
        review_date=review_date,
        days_due=days_due,
    )

    subject = f"ACTION REQUIRED: Model Review Due - {model_name}"

    return EmailFile(
        aap_group_id=aap_group_id,
        subject=subject,
        environment="Discovery",
        body=body,
        model_name=model_name,
    )


# ============================================================================
# INFRASTRUCTURE (FILE SYSTEM)
# ============================================================================

def write_email_json_file(
    email_file: EmailFile,
    output_dir: str,
) -> Path:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    filename = sanitise_json_file_name(
        email_file.aap_group_id,
        email_file.model_name,
    )

    filepath = Path(output_dir) / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(email_file.to_dict(), f, indent=2, ensure_ascii=False)

    return filepath


# ============================================================================
# ORCHESTRATION / PIPELINE
# ============================================================================

def generate_email_data(
    df: pd.DataFrame,
    column_mapping: Dict[str, str],
    output_dir: str = "./email_data",
) -> pd.DataFrame:

    if df is None or df.empty:
        raise ValueError("Empty DataFrame provided")

    missing = set(column_mapping.values()) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    result = df.copy()
    result["json_writing"] = "unsuccessful"

    for idx, row in result.iterrows():
        try:
            email = create_email_data(
                row,
                column_mapping,
                html_renderer=generate_model_review_html,
            )
            write_email_json_file(email, output_dir)
            result.at[idx, "json_writing"] = "successful"
        except Exception as e:
            print(f"Row {idx} failed: {e}")

    return result

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def main():
    """Example usage of the email generation pipeline."""

    print("Email Data Generation")
    print("=" * 60)

    # Define column mapping (logical → actual column names)
    column_mapping = {
        "model_name": "model_name",
        "repo_link": "repo_link",
        "review_date": "review_date",
        "days_due": "days_due",
        "aap_group_id": "aap_group_id",
    }

    # Sample input data
    df_input = pd.DataFrame({
        "model_name": ["ModelA", "ModelB", "ModelC"],
        "repo_link": [
            "https://repo.com/modelA",
            "https://repo.com/modelB",
            "https://repo.com/modelC",
        ],
        "review_date": ["2026-02-15", "2026-02-20", "2026-02-25"],
        "days_due": ["15", "19", "24"],
        "aap_group_id": ["AAP001", "AAP002", "AAP003"],
    })

    print("\n1. Input DataFrame:")
    print(df_input)

    print("\n2. Generating email data files...\n")

    df_output = generate_email_data(
        df_input,
        column_mapping=column_mapping,
        output_dir="./model_review_emails",
    )

    print("3. Output DataFrame (with tracking):")
    print(df_output[["model_name", "aap_group_id", "json_writing"]])

    successful = (df_output["json_writing"] == "successful").sum()
    unsuccessful = len(df_output) - successful

    print("\n4. Summary:")
    print(f"   Total rows: {len(df_output)}")
    print(f"   Successful: {successful}")
    print(f"   Unsuccessful: {unsuccessful}")

    if unsuccessful > 0:
        print("\nRows that failed:")
        print(df_output[df_output["json_writing"] == "unsuccessful"])

    return df_output


if __name__ == "__main__":
    df_result = main()

    print("\n" + "=" * 60)
    print("FILES GENERATED")
    print("=" * 60)
    print("\nFormat: {aap_group_id}_{model_name}.json")
    print("Example: AAP001_ModelA.json")