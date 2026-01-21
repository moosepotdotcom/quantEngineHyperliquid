import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    print("🔒 STARTING SECURITY AUDIT...")
    
    # 1. Login ADMIN
    print("\n1. Testing Admin Login...")
    resp = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": "admin123"})
    if resp.status_code == 200:
        admin_token = resp.json()['access_token']
        role = resp.json()['role']
        if role == 'admin':
            print("   ✅ Admin Login Success (Role: admin)")
        else:
            print(f"   ❌ Role Mismatch: {role}")
    else:
        print(f"   ❌ Admin Login Failed: {resp.text}")
        return

    # 2. Login SUBSCRIBER
    print("\n2. Testing Subscriber Login...")
    resp = requests.post(f"{BASE_URL}/token", data={"username": "test_user", "password": "password123"})
    if resp.status_code == 200:
        sub_token = resp.json()['access_token']
        role = resp.json()['role']
        if role == 'subscriber':
            print("   ✅ Subscriber Login Success (Role: subscriber)")
        else:
            print(f"   ❌ Role Mismatch: {role}")
    else:
        print(f"   ❌ Subscriber Login Failed: {resp.text}")
        return

    # 3. Security Check: Subscriber trying to access Admin Route
    print("\n3. Testing Access Control (RBAC)...")
    print("   [Subscriber] accessing GET /saas/subscribers (Admin Only)...")
    headers = {"Authorization": f"Bearer {sub_token}"}
    resp = requests.get(f"{BASE_URL}/saas/subscribers", headers=headers)
    
    if resp.status_code == 403:
        print("   ✅ ACCESS DENIED (403) - Security Working")
    elif resp.status_code == 200:
        print("   ❌ SECURITY BREACH: Subscriber accessed Admin Route!")
    else:
        print(f"   ❓ Unexpected Status: {resp.status_code}")

    # 4. Verification: Admin trying to access Admin Route
    print("   [Admin] accessing GET /saas/subscribers...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.get(f"{BASE_URL}/saas/subscribers", headers=headers)
    
    if resp.status_code == 200:
        count = len(resp.json())
        print(f"   ✅ ACCESS GRANTED - Admin retrieved {count} subscribers.")
    else:
        print(f"   ❌ Admin Access Failed: {resp.status_code}")

    print("\n✨ SECURITY AUDIT COMPLETE.")

if __name__ == "__main__":
    run_test()
