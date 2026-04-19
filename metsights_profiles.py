"""
MetSights Profiles API: create participant profile and assign an assessment record.

Uses METSIGHTS_BASE_URL and METSIGHTS_API_KEY from the environment (see PROFILES_API.md).
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Literal, Optional

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

AssessmentType = Literal["1", "2"]


def _base_url() -> str:
    return (os.environ.get("METSIGHTS_BASE_URL") or "https://api.metsights.com").rstrip("/")


def _api_key() -> Optional[str]:
    key = (os.environ.get("METSIGHTS_API_KEY") or "").strip()
    return key or None


def phone_for_metsights(phone: str) -> str:
    """Normalize to international format without hyphens (e.g. +91XXXXXXXXXX)."""
    p = (phone or "").strip().replace(" ", "").replace("-", "")
    if p.startswith("+"):
        return p
    if re.match(r"^[1-9]\d{9}$", p):
        return f"+91{p}"
    return p


def gender_code_for_profiles(gender: str) -> str:
    """API expects '1' (male) or '2' (female). Form values are M / F."""
    g = (gender or "").strip().upper()
    return "2" if g == "F" else "1"


def profiles_api_configured() -> bool:
    return _api_key() is not None


def sync_booking_to_metsights(booking_data: Dict[str, Any], assessment_type: AssessmentType) -> bool:
    """
    POST /profiles/ then POST /profiles/:id/records/ with assessment_type.

    assessment_type: '1' = MetSights Basic (MET_BASIC), '2' = MetSights Pro (MET_PRO).
    """
    api_key = _api_key()
    if not api_key:
        print("[METSIGHTS] METSIGHTS_API_KEY is not set; skipping Profiles API")
        return False

    base = _base_url()
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    phone = phone_for_metsights(str(booking_data.get("phone", "")))
    gender = gender_code_for_profiles(str(booking_data.get("gender", "")))

    payload: Dict[str, Any] = {
        "first_name": str(booking_data.get("first_name", "")).strip(),
        "last_name": str(booking_data.get("last_name", "")).strip(),
        "phone": phone,
        "gender": gender,
        "age": int(booking_data["age"]),
    }
    email = (booking_data.get("email") or "").strip()
    if email:
        payload["email"] = email

    profiles_url = f"{base}/profiles/"
    try:
        r = requests.post(profiles_url, json=payload, headers=headers, timeout=15)
        body = r.json() if r.text else {}
    except Exception as e:
        print(f"[METSIGHTS] Profile create request failed: {e}")
        return False

    if not r.ok:
        print(f"[METSIGHTS] Profile create error {r.status_code}: {r.text}")
        return False

    data = body.get("data") if isinstance(body, dict) else None
    profile_id = data.get("id") if isinstance(data, dict) else None
    if not profile_id:
        print(f"[METSIGHTS] Profile create missing id in response: {body}")
        return False

    records_url = f"{base}/profiles/{profile_id}/records/"
    record_payload = {"assessment_type": assessment_type}
    try:
        r2 = requests.post(records_url, json=record_payload, headers=headers, timeout=15)
    except Exception as e:
        print(f"[METSIGHTS] Record create request failed: {e}")
        return False

    if not r2.ok:
        print(f"[METSIGHTS] Record create error {r2.status_code}: {r2.text}")
        return False

    label = "MET_BASIC" if assessment_type == "1" else "MET_PRO"
    print(f"[METSIGHTS] Profile {profile_id} created; {label} record assigned.")
    return True
