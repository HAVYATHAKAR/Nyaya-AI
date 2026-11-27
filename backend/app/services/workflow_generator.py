"""Workflow generator: detect case type from a doc + description, then produce
a personalized step-by-step workflow + checklist + prep score."""
from typing import List, Dict, Any, Optional
from loguru import logger

from .llm_service import llm_service
from ..api.schemas import WorkflowOut


WORKFLOW_PROMPT = """You are NyayaAI's workflow planner. Based on the case description and any
document context below, produce a STRICT JSON object (no markdown) with this exact schema:

{{
  "case_type": "one of: property_dispute, consumer_grievance, employment_issue, family_matter, criminal, tax_dispute, rti_application, civil_suit, other",
  "summary": "1-2 sentence summary of the user's situation",
  "steps": [
    {{
      "step": 1,
      "title": "Short action title (3-6 words)",
      "description": "Detailed guidance on what to do, how, where, and why",
      "deadline_days": null or integer (days from today by which this should be done),
      "priority": "high|medium|low"
    }}
  ],
  "checklist": ["Document or item 1 the user should collect/prepare", "..."],
  "prep_score": 0-100 (estimated readiness score after completing all steps)
}}

Case description / user's situation:
{description}

Document context (if any):
{doc_context}
"""


# Fallback workflows used if LLM is unreachable
FALLBACK_WORKFLOWS = {
    "property_dispute": {
        "case_type": "property_dispute",
        "summary": "Property dispute workflow (template — fill in details).",
        "steps": [
            {"step": 1, "title": "Collect property documents",
             "description": "Gather sale deed, title chain, tax receipts, encumbrance certificate, mutation records.",
             "deadline_days": 14, "priority": "high"},
            {"step": 2, "title": "Obtain certified copies",
             "description": "Visit the Sub-Registrar office to obtain certified copies of registration documents.",
             "deadline_days": 21, "priority": "high"},
            {"step": 3, "title": "Identify the right court/authority",
             "description": "Civil suits for property are filed in the court with jurisdiction over the property location.",
             "deadline_days": 30, "priority": "medium"},
            {"step": 4, "title": "Consult an advocate",
             "description": "Share your organized documents with a property lawyer. Ask for an opinion in writing.",
             "deadline_days": 14, "priority": "high"},
            {"step": 5, "title": "File written reply or suit",
             "description": "If you've received a notice, file a written reply within the deadline. Otherwise file a suit.",
             "deadline_days": 30, "priority": "high"},
            {"step": 6, "title": "Track court dates",
             "description": "Add all court dates to a calendar with reminders 7 days in advance.",
             "deadline_days": None, "priority": "medium"},
        ],
        "checklist": [
            "Sale deed / title document",
            "Property tax receipts (last 3 years)",
            "Encumbrance certificate",
            "Mutation entries (khatian/patta)",
            "Approved building plan (if applicable)",
            "Identity proof (Aadhaar/PAN)",
            "Photographs of the property",
        ],
        "prep_score": 35,
    },
    "consumer_grievance": {
        "case_type": "consumer_grievance",
        "summary": "Consumer complaint workflow (template — fill in details).",
        "steps": [
            {"step": 1, "title": "Send written notice to seller",
             "description": "Send a written complaint to the seller/service provider giving them 14-30 days to respond.",
             "deadline_days": 7, "priority": "high"},
            {"step": 2, "title": "Collect proof of purchase & defect",
             "description": "Bill/invoice, warranty card, photos/videos of defect, correspondence with seller.",
             "deadline_days": 14, "priority": "high"},
            {"step": 3, "title": "Identify Consumer Forum",
             "description": "District Forum (≤Rs.50L), State Commission (Rs.50L-2Cr), National (>Rs.2Cr).",
             "deadline_days": 14, "priority": "medium"},
            {"step": 4, "title": "Draft consumer complaint",
             "description": "Use NyayaAI's Draft Generator to produce a complaint draft under Consumer Protection Act 2019.",
             "deadline_days": 21, "priority": "high"},
            {"step": 5, "title": "File complaint + pay fee",
             "description": "File at the Consumer Forum with jurisdiction. Pay the prescribed fee based on claim value.",
             "deadline_days": 30, "priority": "high"},
        ],
        "checklist": [
            "Invoice / bill of purchase",
            "Warranty card / guarantee certificate",
            "Proof of payment (bank statement/UPI)",
            "Photos/videos of the defect",
            "Copy of written complaint sent to seller",
            "Proof of delivery of notice (courier receipt)",
            "ID proof",
        ],
        "prep_score": 40,
    },
    "rti_application": {
        "case_type": "rti_application",
        "summary": "RTI application workflow (template — fill in details).",
        "steps": [
            {"step": 1, "title": "Identify the Public Authority",
             "description": "Determine which government department holds the information you need.",
             "deadline_days": 3, "priority": "high"},
            {"step": 2, "title": "Draft RTI application",
             "description": "Use NyayaAI's Draft Generator. Be specific — vague RTIs get rejected.",
             "deadline_days": 5, "priority": "high"},
            {"step": 3, "title": "Pay Rs.10 fee",
             "description": "Pay by IPO, court fee stamp, or online via Bharat Kosh (for central govt).",
             "deadline_days": 7, "priority": "high"},
            {"step": 4, "title": "Submit & keep proof",
             "description": "Submit by post or in person. Keep the receiving/acknowledgement copy.",
             "deadline_days": 7, "priority": "high"},
            {"step": 5, "title": "Wait 30 days for PIO response",
             "description": "PIO must respond within 30 days (48 hrs if life/liberty involved).",
             "deadline_days": 30, "priority": "medium"},
            {"step": 6, "title": "File First Appeal if no reply",
             "description": "If no response in 30 days or unsatisfied, file First Appeal within 30 days to designated FAA.",
             "deadline_days": 60, "priority": "medium"},
        ],
        "checklist": [
            "Subject / topic of information requested",
            "Specific questions (numbered, clear)",
            "Department name & PIO address",
            "Fee payment instrument (IPO / court fee / online receipt)",
            "Self-addressed stamped envelope (for postal reply)",
            "Your ID proof",
        ],
        "prep_score": 50,
    },
    "default": {
        "case_type": "other",
        "summary": "Generic legal preparation workflow.",
        "steps": [
            {"step": 1, "title": "Gather all related documents",
             "description": "Notices, agreements, correspondence, ID proof, photos.",
             "deadline_days": 7, "priority": "high"},
            {"step": 2, "title": "Note all deadlines",
             "description": "List every date mentioned in any document with what's due.",
             "deadline_days": 3, "priority": "high"},
            {"step": 3, "title": "Consult a qualified advocate",
             "description": "Carry your organized documents and a written summary.",
             "deadline_days": 14, "priority": "high"},
            {"step": 4, "title": "Prepare written timeline",
             "description": "Chronological order of events helps your advocate assess the case quickly.",
             "deadline_days": 7, "priority": "medium"},
        ],
        "checklist": [
            "All relevant legal documents",
            "ID proof",
            "Address proof",
            "Photographs / evidence",
            "List of witnesses with contact info",
            "Written timeline of events",
        ],
        "prep_score": 30,
    },
}


def pick_fallback(case_type: str) -> Dict[str, Any]:
    return FALLBACK_WORKFLOWS.get(case_type, FALLBACK_WORKFLOWS["default"])


async def generate_workflow(
    description: Optional[str] = None,
    doc_context: Optional[str] = None,
    case_type_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a personalized workflow for the user's situation."""
    desc = description or "(no description provided)"
    ctx = doc_context or "(no document context available)"

    prompt = WORKFLOW_PROMPT.format(description=desc, doc_context=ctx)
    messages = [{"role": "user", "content": prompt}]

    try:
        raw = await llm_service.chat(messages, max_new_tokens=1000, temperature=0.3)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            if raw.endswith("```"):
                raw = raw[:-3]
        data = __import__("json").loads(raw.strip())
        # Ensure required keys exist
        data["analysis_status"] = "available"
        data["deadline_notice"] = "Generated timeframes are planning estimates, not legally binding deadlines."
        validated = WorkflowOut.model_validate(data)
        return validated.model_dump()
    except Exception as e:
        logger.warning("Workflow generation unavailable or invalid ({})", type(e).__name__)
        fallback = dict(pick_fallback(case_type_hint or "other"))
        fallback["analysis_status"] = "template_fallback"
        fallback["deadline_notice"] = "Template timeframes are illustrative planning estimates, not legal deadlines. Verify requirements with an advocate or authoritative source."
        return WorkflowOut.model_validate(fallback).model_dump()
