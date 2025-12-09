import requests
import os

from dotenv import load_dotenv

load_dotenv()

SHIPYAARI_API_URL = "https://backend.api-wa.co/campaign/shipyaari/api/v2"
SHIPYAARI_API_KEY = os.getenv("SHIPYAARI_API_KEY")
user_name = "Fitnastic"


def send_msg(CAMPAIGN_NAME, destination_phone, templateParams):
    if not SHIPYAARI_API_KEY:
        return "Error: SHIPYAARI_API_KEY is not set on the server.", 500

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
            # Show an error if something went wrong
            print(f"Error sending message. Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        # Handle network errors
        print(f"Network error: {e}")
        return False
    except Exception as e:
        # Handle any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        return False
