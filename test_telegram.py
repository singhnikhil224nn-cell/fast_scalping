import os
import requests
from dotenv import load_dotenv

# Load local environment variables if testing locally, otherwise Render handles it natively
load_dotenv()

def test_cloud_bridge():
    # Use the exact variable keys you have saved in your Render dashboard
    token = "8992654694:AAHXHrcq8YsppzFUlSRH99CAdQ9dmUUnnQo"
    chat_id = "7366145742"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🚀 RENDER CLOUD SUCCESS: Isolated testing pipeline completely operational!"
    }
    
    print("Firing isolated system test to Telegram...")
    response = requests.post(url, json=payload)
    print(f"Telegram Server Response: {response.json()}")

if __name__ == "__main__":
    test_cloud_bridge()
