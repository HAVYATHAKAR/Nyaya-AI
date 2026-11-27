"""Draft generator: Jinja2 templates for common Indian legal documents."""
from pathlib import Path
from typing import Dict, Any
from html import escape
from loguru import logger

from jinja2 import Environment, FileSystemLoader, select_autoescape


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(disabled_extensions=("txt",), default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)


# Template registry: human label → (filename, required_fields, description)
TEMPLATES = {
    "rti": {
        "label": "RTI Application",
        "file": "rti_application.txt.j2",
        "description": "Right to Information Act, 2005 — application to Public Information Officer.",
        "fields": [
            {"name": "applicant_name", "label": "Your full name", "required": True},
            {"name": "applicant_address", "label": "Your full address", "required": True},
            {"name": "applicant_phone", "label": "Phone number", "required": False},
            {"name": "applicant_email", "label": "Email", "required": False},
            {"name": "pio_name", "label": "Public Information Officer name (or 'PIO, <Dept>')", "required": True},
            {"name": "department", "label": "Department / Public Authority", "required": True},
            {"name": "department_address", "label": "Department address", "required": True},
            {"name": "subject", "label": "Subject of the application (short)", "required": True},
            {"name": "information_requested", "label": "Specific information you want (number each item)", "required": True, "textarea": True},
            {"name": "period", "label": "Time period the info relates to (optional)", "required": False},
        ],
    },
    "consumer_complaint": {
        "label": "Consumer Complaint",
        "file": "consumer_complaint.txt.j2",
        "description": "Consumer Protection Act, 2019 — complaint to Consumer Forum.",
        "fields": [
            {"name": "complainant_name", "label": "Your name", "required": True},
            {"name": "complainant_address", "label": "Your address", "required": True},
            {"name": "complainant_phone", "label": "Phone", "required": False},
            {"name": "opposite_party_name", "label": "Seller/service provider name", "required": True},
            {"name": "opposite_party_address", "label": "Seller address", "required": True},
            {"name": "forum", "label": "District / State / National Forum", "required": True},
            {"name": "purchase_date", "label": "Date of purchase", "required": True},
            {"name": "product_service", "label": "Product/service description", "required": True},
            {"name": "amount_paid", "label": "Amount paid (Rs.)", "required": True},
            {"name": "invoice_number", "label": "Invoice/bill number", "required": False},
            {"name": "defect_grievance", "label": "Defect / grievance description", "required": True, "textarea": True},
            {"name": "relief_sought", "label": "Relief sought (refund/replace/Damages)", "required": True, "textarea": True},
            {"name": "claim_value", "label": "Total claim value (Rs.)", "required": True},
        ],
    },
    "legal_notice": {
        "label": "Legal Notice",
        "file": "legal_notice.txt.j2",
        "description": "General legal notice — sent before filing a civil/criminal case.",
        "fields": [
            {"name": "sender_name", "label": "Notice sender name", "required": True},
            {"name": "sender_address", "label": "Sender address", "required": True},
            {"name": "recipient_name", "label": "Notice recipient name", "required": True},
            {"name": "recipient_address", "label": "Recipient address", "required": True},
            {"name": "subject", "label": "Subject of the notice", "required": True},
            {"name": "facts", "label": "Statement of facts (chronological)", "required": True, "textarea": True},
            {"name": "grievance", "label": "Specific grievance / wrong done", "required": True, "textarea": True},
            {"name": "relief_demanded", "label": "Relief demanded", "required": True, "textarea": True},
            {"name": "notice_period_days", "label": "Notice period in days (e.g. 15, 30)", "required": True},
        ],
    },
    "affidavit": {
        "label": "General Affidavit",
        "file": "affidavit.txt.j2",
        "description": "General-purpose sworn affidavit format (used for name change, ID corrections, declarations).",
        "fields": [
            {"name": "deponent_name", "label": "Deponent full name", "required": True},
            {"name": "deponent_age", "label": "Age", "required": True},
            {"name": "deponent_address", "label": "Address", "required": True},
            {"name": "deponent_occupation", "label": "Occupation", "required": False},
            {"name": "declaration", "label": "Statement being declared under oath", "required": True, "textarea": True},
        ],
    },
    "rental_agreement": {
        "label": "Rental Agreement",
        "file": "rental_agreement.txt.j2",
        "description": "Residential rental/lease agreement (11-month standard).",
        "fields": [
            {"name": "owner_name", "label": "Owner full name", "required": True},
            {"name": "owner_address", "label": "Owner address", "required": True},
            {"name": "tenant_name", "label": "Tenant full name", "required": True},
            {"name": "tenant_address", "label": "Tenant address (current)", "required": True},
            {"name": "property_address", "label": "Property being rented (full address)", "required": True},
            {"name": "monthly_rent", "label": "Monthly rent (Rs.)", "required": True},
            {"name": "deposit", "label": "Security deposit (Rs.)", "required": True},
            {"name": "tenure_months", "label": "Tenure in months (e.g. 11)", "required": True},
            {"name": "start_date", "label": "Start date (YYYY-MM-DD)", "required": True},
            {"name": "notice_period_days", "label": "Notice period to vacate (days)", "required": True},
        ],
    },
}


def list_templates() -> Dict[str, Dict[str, Any]]:
    """Return metadata for all available templates."""
    return {
        key: {
            "label": t["label"],
            "description": t["description"],
            "fields": t["fields"],
        }
        for key, t in TEMPLATES.items()
    }


def generate_draft(template_key: str, fields: Dict[str, Any]) -> str:
    """Render a draft from the specified template + filled fields."""
    if template_key not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_key}")

    tmpl_info = TEMPLATES[template_key]
    allowed = {field["name"] for field in tmpl_info["fields"]}
    if not isinstance(fields, dict):
        raise ValueError("Draft fields must be an object")
    if set(fields) - allowed:
        raise ValueError("Unknown draft fields supplied")
    template = env.get_template(tmpl_info["file"])

    # Fill missing fields with placeholders so the user sees what to complete
    final_fields = {}
    for f in tmpl_info["fields"]:
        val = fields.get(f["name"], "")
        if val is not None and not isinstance(val, (str, int, float)):
            raise ValueError(f"Invalid value for {f['label']}")
        val = str(val).strip()[:4000] if val is not None else ""
        if not val:
            if f.get("required"):
                final_fields[f["name"]] = f"<<FILL: {f['label']}>>"
            else:
                final_fields[f["name"]] = ""
        else:
            # These are plain-text templates; HTML-escape user data before it is
            # returned to clients that might render the result in an HTML view.
            final_fields[f["name"]] = escape(val, quote=True)

    rendered = template.render(**final_fields)

    # Append disclaimer
    disclaimer = (
        "\n\n" + "=" * 60 + "\n"
        "DISCLAIMER: This draft was generated by NyayaAI's AI-powered draft\n"
        "generator and is intended as a preliminary document only. Please\n"
        "have it reviewed by a qualified legal professional before use.\n"
        + "=" * 60
    )
    return rendered + disclaimer
