"""
Meritto CRM Service for sending leads and inquiries to Meritto platform.
Handles async communication with Meritto API endpoints.
"""
import asyncio
import httpx
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class MeritoCRMService:
    """Service to integrate with Meritto CRM API."""
    
    BASE_URL = "https://api.nopaperforms.io"
    CREATE_LEAD_ENDPOINT = "/lead/v1/create"
    REQUEST_TIMEOUT = 30  # seconds
    
    def __init__(self):
        """Initialize the Meritto CRM service."""
        self.secret_key = settings.MERITTO_SECRET_KEY
        self.access_key = settings.MERITTO_ACCESS_KEY
        self.is_enabled = bool(self.secret_key and self.access_key)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Meritto API requests."""
        return {
            "secret-key": self.secret_key,
            "access-key": self.access_key,
            "Content-Type": "application/json"
        }
    
    async def send_lead(
        self,
        name: str,
        email: str,
        mobile: str,
        country_dial_code: str = "+91",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Send a lead to Meritto CRM asynchronously.
        
        Args:
            name: Customer/Inquirer name
            email: Customer email
            mobile: Customer mobile number
            country_dial_code: Country dial code (default: +91 for India)
            **kwargs: Additional fields to send
            
        Returns:
            Response from Meritto API or None if disabled/failed
        """
        if not self.is_enabled:
            logger.warning("Meritto CRM is not configured. Skipping lead sync.")
            return None
        
        try:
            payload = {
                "name": name,
                "email": email,
                "country_dial_code": country_dial_code,
                "mobile": mobile,
                **kwargs
            }
            
            url = f"{self.BASE_URL}{self.CREATE_LEAD_ENDPOINT}"
            
            # Use asyncio.to_thread to make HTTP call non-blocking
            response = await asyncio.to_thread(
                self._make_request,
                url,
                payload
            )
            
            logger.info(
                f"[MERITTO CRM] Lead created successfully. "
                f"Name: {name}, Email: {email}, Mobile: {mobile}"
            )
            return response
            
        except Exception as e:
            logger.error(
                f"[MERITTO CRM] Failed to send lead: {name} ({email}). "
                f"Error: {str(e)}"
            )
            return None
    
    def _make_request(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make synchronous HTTP request to Meritto API.
        This method runs in a thread pool to avoid blocking async code.
        
        Args:
            url: API endpoint URL
            payload: Request payload
            
        Returns:
            Response from API
        """
        with httpx.Client(timeout=self.REQUEST_TIMEOUT) as client:
            response = client.post(
                url,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def send_inquiry_to_crm(
        self,
        name: str,
        email: str,
        phone_number: str,
        course_interested: Optional[str] = None,
        message: Optional[str] = None,
        college_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send an inquiry submission to Meritto CRM.
        
        Args:
            name: Inquirer name
            email: Inquirer email
            phone_number: Inquirer phone number
            course_interested: Course name they're interested in
            message: Inquiry message
            college_name: College name for context
            
        Returns:
            Response from API or None if failed
        """
        extra_fields = {}
        
        if course_interested:
            extra_fields["course"] = course_interested
        
        if message:
            extra_fields["message"] = message
        
        if college_name:
            extra_fields["college"] = college_name
        
        # Clean phone number (remove special characters, keep digits only)
        phone_clean = ''.join(filter(str.isdigit, phone_number))
        
        return await self.send_lead(
            name=name,
            email=email,
            mobile=phone_clean,
            country_dial_code="+91",
            **extra_fields
        )
    
    async def send_contact_to_crm(
        self,
        name: str,
        email: str,
        phone_no: str,
        state: Optional[str] = None,
        city: Optional[str] = None,
        address: Optional[str] = None,
        message: Optional[str] = None,
        college_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a contact form submission to Meritto CRM.
        
        Args:
            name: Contact name
            email: Contact email
            phone_no: Contact phone number
            state: Contact state
            city: Contact city
            address: Contact address
            message: Contact message
            college_name: College name for context
            
        Returns:
            Response from API or None if failed
        """
        extra_fields = {}
        
        if state:
            extra_fields["state"] = state
        
        if city:
            extra_fields["city"] = city
        
        if address:
            extra_fields["address"] = address
        
        if message:
            extra_fields["inquiry"] = message
        
        if college_name:
            extra_fields["college"] = college_name
        
        # Clean phone number
        phone_clean = ''.join(filter(str.isdigit, phone_no))
        
        return await self.send_lead(
            name=name,
            email=email,
            mobile=phone_clean,
            country_dial_code="+91",
            **extra_fields
        )


# Global instance
meritto_service = MeritoCRMService()
