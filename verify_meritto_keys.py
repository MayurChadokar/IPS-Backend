"""
Quick Meritto API credential verification.
Tests if your API keys work with a simple lead creation.

Run this after restarting your application.
"""

import asyncio
import httpx
import json


async def verify_credentials():
    """Verify Meritto API credentials work."""
    
    # Your credentials from .env
    SECRET_KEY = "f70d121075f002fd05c97a36cb3f8844"
    ACCESS_KEY = "afd36d8368544019928438e61625e760"
    
    print("\n" + "="*70)
    print("MERITTO API CREDENTIAL VERIFICATION")
    print("="*70)
    
    print(f"\nCredentials:")
    print(f"  SECRET_KEY: {SECRET_KEY[:16]}...{SECRET_KEY[-16:]}")
    print(f"  ACCESS_KEY: {ACCESS_KEY[:16]}...{ACCESS_KEY[-16:]}")
    
    headers = {
        "secret-key": SECRET_KEY,
        "access-key": ACCESS_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": "Verification Test",
        "email": "verify@test.com",
        "country_dial_code": "+91",
        "mobile": "9999999999"
    }
    
    print(f"\nSending test request...")
    print(f"  URL: https://api.nopaperforms.io/lead/v1/create")
    print(f"  Payload: {json.dumps(payload, indent=2)}")
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.nopaperforms.io/lead/v1/create",
                headers=headers,
                json=payload
            )
        
        print(f"\n✅ Response Status: {response.status_code}")
        
        try:
            resp_json = response.json()
            print(f"\nResponse:")
            print(json.dumps(resp_json, indent=2))
            
            if response.status_code == 200:
                print("\n🎉 SUCCESS! API credentials are valid!")
                return True
            elif response.status_code == 401:
                print("\n❌ AUTHENTICATION FAILED!")
                print("\nPossible causes:")
                print("  1. API key is inactive in Meritto account")
                print("  2. API key has expired")
                print("  3. API key is incorrect (copy-paste error?)")
                print("  4. Account doesn't have API access enabled")
                return False
            else:
                print(f"\n⚠️  Received status code: {response.status_code}")
                return False
                
        except:
            print(f"\nRaw Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    asyncio.run(verify_credentials())
