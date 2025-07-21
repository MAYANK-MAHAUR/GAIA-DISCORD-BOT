import requests

url = "https://0xcedbfd0b2d8e1f940c76c9c587c8ba12a62ecd32.gaia.domains/v1/chat/completions"

headers = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Bearer gaia-MGM5ZDQyNTMtNjNlMy00ZTUwLWJhNjUtNWY2MWVlNWVhY2Q5-vGUC-ENYLONoGjYm"  # Replace with your full API key
}

data = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Where is Paris?"}
    ],
    "model": "Qwen2-0.5B"
}

try:
    response = requests.post(url, headers=headers, json=data)
    print(response.json())
except requests.exceptions.RequestException as e:
    print("Connection error:", e)
