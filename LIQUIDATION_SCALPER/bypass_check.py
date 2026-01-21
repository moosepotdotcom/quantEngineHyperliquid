
import requests
import urllib3

urllib3.disable_warnings()

ip_address = "18.67.161.72" # Captured from previous ping
host = "api.hyperliquid.xyz"
url = f"https://{ip_address}/info"

print(f"Attempting Host Header Bypass to {ip_address}...")
headers = {"Host": host}

try:
    response = requests.get(url, headers=headers, verify=False, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:100]}...")
    if response.status_code == 200:
        print("✅ SUCCESS! We bypassed the DNS block.")
    else:
        print("❌ Failed (HTTP Error)")
except Exception as e:
    print(f"❌ Failed (Connection Error): {e}")
