"""
Debug utility to test Meritto API connection and credentials.
Helps identify authentication and connectivity issues.

Usage:
    python debug_meritto_connection.py
"""

import httpx
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text):
    print(f"\n{text}")
    print("-" * 70)


async def test_raw_connection():
    """Test raw HTTP connection with your credentials."""
    print_section("1. Testing Raw HTTP Connection")
    
    secret_key = settings.MERITTO_SECRET_KEY
    access_key = settings.MERITTO_ACCESS_KEY
    
    if not secret_key or not access_key:
        print("❌ Missing credentials in .env")
        print(f"   MERITTO_SECRET_KEY: {'SET' if secret_key else 'NOT SET'}")
        print(f"   MERITTO_ACCESS_KEY: {'SET' if access_key else 'NOT SET'}")
        return False
    
    print(f"✅ Credentials found")
    print(f"   SECRET_KEY: {secret_key[:10]}...{secret_key[-10:]}")
    print(f"   ACCESS_KEY: {access_key[:10]}...{access_key[-10:]}")
    
    # Test data
    test_payload = {
        "name": "Debug Test",
        "email": "debug.test@example.com",
        "country_dial_code": "+91",
        "mobile": "9999999999"
    }
    
    headers = {
        "secret-key": secret_key,
        "access-key": access_key,
        "Content-Type": "application/json"
    }
    
    print(f"\nRequest Details:")
    print(f"  URL: https://api.nopaperforms.io/lead/v1/create")
    print(f"  Method: POST")
    print(f"  Headers:")
    print(f"    - secret-key: {secret_key[:10]}...***")
    print(f"    - access-key: {access_key[:10]}...***")
    print(f"    - Content-Type: application/json")
    print(f"  Payload:")
    print(f"    {json.dumps(test_payload, indent=4)}")
    
    try:
        print(f"\n⏳ Sending request...")
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.nopaperforms.io/lead/v1/create",
                headers=headers,
                json=test_payload
            )
        
        print(f"\n✅ Response received!")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'content-length', 'server', 'date']:
                print(f"    - {key}: {value}")
        
        print(f"\n  Response Body:")
        try:
            resp_json = response.json()
            print(f"    {json.dumps(resp_json, indent=4)}")
        except:
            print(f"    {response.text}")
        
        if response.status_code == 200:
            print(f"\n🎉 SUCCESS! API credentials are valid and working!")
            return True
        elif response.status_code == 401:
            print(f"\n❌ AUTHENTICATION FAILED (401)")
            print(f"\nPossible causes:")
            print(f"  1. API credentials are incorrect")
            print(f"  2. API credentials have expired")
            print(f"  3. API credentials are inactive in Meritto account")
            print(f"  4. Wrong secret-key or access-key")
            return False
        else:
            print(f"\n⚠️  Unexpected response code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Connection Error: {str(e)}")
        print(f"\nPossible causes:")
        print(f"  1. Network/Firewall blocking API calls")
        print(f"  2. DNS resolution failure")
        print(f"  3. Meritto API server is down")
        return False


def check_credentials():
    """Check if credentials are properly configured."""
    print_section("Credential Verification")
    
    secret_key = settings.MERITTO_SECRET_KEY
    access_key = settings.MERITTO_ACCESS_KEY
    
    print(f"Secret Key Status:    {'✅ SET' if secret_key else '❌ NOT SET'}")
    print(f"Access Key Status:    {'✅ SET' if access_key else '❌ NOT SET'}")
    
    if secret_key:
        print(f"\nSecret Key:")
        print(f"  Length: {len(secret_key)} characters")
        print(f"  Type: {type(secret_key).__name__}")
        print(f"  Preview: {secret_key[:16]}...{secret_key[-16:]}")
    
    if access_key:
        print(f"\nAccess Key:")
        print(f"  Length: {len(access_key)} characters")
        print(f"  Type: {type(access_key).__name__}")
        print(f"  Preview: {access_key[:16]}...{access_key[-16:]}")
    
    return bool(secret_key and access_key)


def show_curl_equivalent():
    """Show the equivalent curl command for manual testing."""
    print_section("Equivalent curl Command")
    
    secret_key = settings.MERITTO_SECRET_KEY
    access_key = settings.MERITTO_ACCESS_KEY
    
    if not secret_key or not access_key:
        print("❌ Credentials not set")
        return
    
    curl_cmd = f"""curl --location 'https://api.nopaperforms.io/lead/v1/create' \\
  --header 'secret-key: {secret_key}' \\
  --header 'access-key: {access_key}' \\
  --header 'Content-Type: application/json' \\
  --data-raw '{{
    "name": "Test User",
    "email": "test@example.com",
    "country_dial_code": "+91",
    "mobile": "9999999999"
  }}'"""
    
    print("You can copy and run this curl command in terminal:")
    print("\n" + curl_cmd)


def show_troubleshooting():
    """Show troubleshooting steps."""
    print_section("Troubleshooting Steps")
    
    print("""
1. Verify API Credentials
   - Log in to your Meritto account
   - Navigate to Settings > Integrations > API Keys
   - Confirm the keys match exactly (check for spaces/typos)
   - Copy them again if needed

2. Check API Key Status
   - Ensure the API keys are ACTIVE (not disabled)
   - Check if API access is enabled for your account
   
3. Check IP Whitelist (if enabled)
   - Some accounts have IP whitelisting
   - Check if your server's IP is whitelisted
   - Your server IP might be: 106.202.51.28 (from logs)

4. Test with curl
   - Run the curl command shown above
   - Verify manually that credentials work
   - Check the exact error response

5. Contact Meritto Support
   - If credentials are correct but still getting 401
   - Check Meritto status page for outages
   - Contact their support team with your account details

6. Check Account Permissions
   - Ensure your Meritto account has "Lead Creation" API access
   - Some account types may have API access disabled
    """)


async def main():
    """Run all diagnostics."""
    print_header("MERITTO CRM API - DEBUG & DIAGNOSTIC TOOL")
    
    # Check credentials
    creds_ok = check_credentials()
    
    if not creds_ok:
        print("\n" + "!" * 70)
        print("ERROR: Meritto API credentials are not configured!")
        print("!" * 70)
        print("\nAdd these to your .env file:")
        print("  MERITTO_SECRET_KEY=your_secret_key")
        print("  MERITTO_ACCESS_KEY=your_access_key")
        return
    
    # Show curl equivalent
    show_curl_equivalent()
    
    # Test connection
    print_header("TESTING API CONNECTION")
    connection_ok = await test_raw_connection()
    
    # Show troubleshooting if failed
    if not connection_ok:
        show_troubleshooting()
    
    # Summary
    print_header("DIAGNOSTIC SUMMARY")
    print(f"\n✅ Credentials Configured: {creds_ok}")
    print(f"✅ API Connection: {'WORKING' if connection_ok else 'FAILED'}")
    
    if connection_ok:
        print("\n🎉 Your Meritto CRM integration should be working!")
    else:
        print("\n⚠️  There are issues that need to be resolved.")
        print("See troubleshooting section above.")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
