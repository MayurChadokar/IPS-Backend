"""
Test utility for Meritto CRM service integration.
Run this script to verify your Meritto API credentials and test the service.

Usage:
    python test_meritto_crm.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.services.meritto_crm import meritto_service


async def test_meritto_credentials():
    """Test if Meritto credentials are configured."""
    print("\n" + "="*60)
    print("MERITTO CRM SERVICE - CONFIGURATION TEST")
    print("="*60)
    
    print("\n1. Checking Configuration...")
    print("-" * 60)
    
    if not settings.MERITTO_SECRET_KEY:
        print("❌ MERITTO_SECRET_KEY not configured in .env")
    else:
        print(f"✅ MERITTO_SECRET_KEY: {settings.MERITTO_SECRET_KEY[:10]}...***")
    
    if not settings.MERITTO_ACCESS_KEY:
        print("❌ MERITTO_ACCESS_KEY not configured in .env")
    else:
        print(f"✅ MERITTO_ACCESS_KEY: {settings.MERITTO_ACCESS_KEY[:10]}...***")
    
    if meritto_service.is_enabled:
        print("\n✅ Meritto CRM Service: ENABLED")
    else:
        print("\n❌ Meritto CRM Service: DISABLED (Missing credentials)")
        return False
    
    return True


async def test_lead_creation():
    """Test sending a sample lead to Meritto."""
    print("\n2. Testing Lead Creation...")
    print("-" * 60)
    
    test_lead = {
        "name": "Test User",
        "email": "test.user@example.com",
        "phone_number": "9876543210",
        "course_interested": "MBA",
        "message": "This is a test inquiry from the CRM service."
    }
    
    print(f"\nSending test lead:")
    for key, value in test_lead.items():
        print(f"  - {key}: {value}")
    
    try:
        result = await meritto_service.send_inquiry_to_crm(
            name=test_lead["name"],
            email=test_lead["email"],
            phone_number=test_lead["phone_number"],
            course_interested=test_lead["course_interested"],
            message=test_lead["message"],
            college_name="Test College"
        )
        
        if result:
            print("\n✅ Lead sent successfully!")
            print(f"\nAPI Response:")
            print(f"  {result}")
            return True
        else:
            print("\n⚠️  Lead sent but received no response (check logs for details)")
            return False
            
    except Exception as e:
        print(f"\n❌ Error sending lead: {str(e)}")
        return False


async def test_contact_creation():
    """Test sending a sample contact to Meritto."""
    print("\n3. Testing Contact Form Creation...")
    print("-" * 60)
    
    test_contact = {
        "name": "Contact Test User",
        "email": "contact.test@example.com",
        "phone_no": "9876543211",
        "state": "Maharashtra",
        "city": "Mumbai",
        "address": "123 Test Street, Apt 4B",
        "message": "This is a test contact submission."
    }
    
    print(f"\nSending test contact:")
    for key, value in test_contact.items():
        print(f"  - {key}: {value}")
    
    try:
        result = await meritto_service.send_contact_to_crm(
            name=test_contact["name"],
            email=test_contact["email"],
            phone_no=test_contact["phone_no"],
            state=test_contact["state"],
            city=test_contact["city"],
            address=test_contact["address"],
            message=test_contact["message"],
            college_name="Test College"
        )
        
        if result:
            print("\n✅ Contact sent successfully!")
            print(f"\nAPI Response:")
            print(f"  {result}")
            return True
        else:
            print("\n⚠️  Contact sent but received no response (check logs for details)")
            return False
            
    except Exception as e:
        print(f"\n❌ Error sending contact: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("\n")
    
    # Test configuration
    config_ok = await test_meritto_credentials()
    
    if not config_ok:
        print("\n" + "="*60)
        print("⚠️  CONFIGURATION INCOMPLETE")
        print("="*60)
        print("\nTo enable Meritto CRM integration:")
        print("1. Add your credentials to .env file:")
        print("   MERITTO_SECRET_KEY=your_secret_key")
        print("   MERITTO_ACCESS_KEY=your_access_key")
        print("\n2. Restart your application")
        print("\n3. Run this test again to verify")
        print("\nFor more info, see MERITTO_CRM_CONFIG.md")
        return
    
    # Test lead creation
    lead_ok = await test_lead_creation()
    
    # Test contact creation
    contact_ok = await test_contact_creation()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"\nConfiguration:  {'✅ PASSED' if config_ok else '❌ FAILED'}")
    print(f"Lead Creation:  {'✅ PASSED' if lead_ok else '❌ FAILED'}")
    print(f"Contact Creation: {'✅ PASSED' if contact_ok else '❌ FAILED'}")
    
    if config_ok and lead_ok and contact_ok:
        print("\n🎉 All tests passed! Meritto CRM integration is working.")
    elif config_ok:
        print("\n⚠️  Configuration is correct but API tests failed.")
        print("   This might be due to:")
        print("   - Invalid/expired API credentials")
        print("   - Network/firewall issues")
        print("   - Meritto API server issues")
        print("\n   Check your logs for detailed error messages.")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
