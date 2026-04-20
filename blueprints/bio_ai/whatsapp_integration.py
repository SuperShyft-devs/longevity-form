import requests
import os

from dotenv import load_dotenv

load_dotenv()

SHIPYAARI_API_URL = "https://backend.api-wa.co/campaign/shipyaari/api/v2"
SHIPYAARI_API_KEY = os.getenv("SHIPYAARI_API_KEY")
user_name = "Fitnastic"


def _whatsapp_sending_enabled() -> bool:
    v = (os.getenv("WHATSAPP_NOTIFICATIONS_ENABLED") or "true").strip().lower()
    return v not in ("0", "false", "no", "off")


def send_msg(CAMPAIGN_NAME, destination_phone, templateParams):
    if not SHIPYAARI_API_KEY:
        return "Error: SHIPYAARI_API_KEY is not set on the server.", 500

    if not _whatsapp_sending_enabled():
        print("[Shipyaari/WhatsApp] Skipped (WHATSAPP_NOTIFICATIONS_ENABLED is off)")
        return False

    try:
        # 1. Get user data from your form
        # 2. Format the phone number as required by the docs (+91)
        # 3. Create the JSON payload as specified in the docs
        payload = {
            "apiKey": SHIPYAARI_API_KEY,
            "campaignName": CAMPAIGN_NAME,
            "destination": destination_phone,
            "userName": user_name,
            "templateParams": templateParams,
            "source": "Longevity Bio AI Form",  # Optional: good for tracking
        }

        # 4. Set the headers
        headers = {"Content-Type": "application/json"}

        # 5. Send the POST request to the API
        response = requests.post(SHIPYAARI_API_URL, headers=headers, json=payload)

        # 6. Check the response
        if response.status_code == 200:
            # Redirect to a 'thank you' page
            return True
        else:
            detail = ""
            try:
                body = response.json()
                if isinstance(body, dict) and body.get("errorMessage"):
                    detail = f" — {body.get('errorMessage')}"
            except Exception:
                pass
            print(f"[Shipyaari/WhatsApp] Send failed (status {response.status_code}){detail}")
            print(f"[Shipyaari/WhatsApp] Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        # Handle network errors
        print(f"Network error: {e}")
        return False
    except Exception as e:
        # Handle any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        return False
