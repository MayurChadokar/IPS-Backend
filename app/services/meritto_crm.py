"""
Meritto CRM Service for sending leads and inquiries to Meritto platform.
Handles async communication with Meritto API endpoints with comprehensive logging and retry logic.
"""
import asyncio
import httpx
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import CrmSyncAudit

# Configure detailed logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Also log to console for visibility
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '[%(asctime)s] [MERITTO] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class MeritoCRMService:
    """Service to integrate with Meritto CRM API with enhanced logging and retry logic."""
    
    BASE_URL = "https://api.nopaperforms.io"
    CREATE_LEAD_ENDPOINT = "/lead/v1/create"
    REQUEST_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds, will exponentially backoff
    
    def __init__(self):
        """Initialize the Meritto CRM service."""
        self.secret_key = settings.MERITTO_SECRET_KEY
        self.access_key = settings.MERITTO_ACCESS_KEY
        self.is_enabled = bool(self.secret_key and self.access_key)
        
        # Log initialization status
        logger.info(f"Meritto CRM Service initialized. Enabled: {self.is_enabled}")
        if not self.is_enabled:
            logger.warning("[CONFIG] MERITTO_SECRET_KEY or MERITTO_ACCESS_KEY not configured in .env")
    
    def _log_to_database(
        self,
        entity_type: str,
        entity_id: int,
        entity_email: str,
        entity_name: str,
        status: str,
        error_message: Optional[str] = None,
        response_data: Optional[Dict] = None,
        college_name: Optional[str] = None,
        attempt_count: int = 0
    ):
        """
        Log sync attempt to database for audit trail.
        
        Args:
            entity_type: 'inquiry' or 'contact'
            entity_id: ID of inquiry or contact
            entity_email: Email of the entity
            entity_name: Name of the entity
            status: 'pending', 'success', 'failed', 'retrying'
            error_message: Error message if failed
            response_data: API response data
            college_name: College name
            attempt_count: Number of attempts
        """
        try:
            db = SessionLocal()
            audit_log = CrmSyncAudit(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_email=entity_email,
                entity_name=entity_name,
                college_name=college_name,
                status=status,
                attempt_count=attempt_count,
                last_attempt_at=datetime.now(),
                error_message=error_message,
                response_data=response_data
            )
            db.add(audit_log)
            db.commit()
            db.close()
            logger.debug(f"[DB_LOG] Sync audit logged - {entity_type} {entity_id} ({entity_email}): {status}")
        except Exception as e:
            logger.error(f"[DB_LOG_ERROR] Failed to log to database: {str(e)}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Meritto API requests."""
        headers = {
            "secret-key": self.secret_key,
            "access-key": self.access_key,
            "Content-Type": "application/json"
        }
        logger.debug(f"[HEADERS] Using headers with keys: secret-key={self.secret_key[:10]}**, access-key={self.access_key[:10]}**")
        return headers
    
    def _validate_and_clean_phone(self, phone_number: str) -> tuple[Optional[str], Optional[str]]:
        """
        Validate and clean phone number for India (must be 10 digits).
        
        Args:
            phone_number: Raw phone number (can have +91, dashes, spaces, etc)
            
        Returns:
            Tuple of (cleaned_number, error_message). If valid, error_message is None.
            Example: ("9876543210", None) or (None, "Phone must contain exactly 10 digits")
        """
        logger.debug(f"[PHONE_VALIDATE] Input: {phone_number}")
        
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone_number))
        logger.debug(f"[PHONE_VALIDATE] After digit extraction: {digits_only}")
        
        # Remove country code if present (+91 or 91)
        if digits_only.startswith('91') and len(digits_only) == 12:
            digits_only = digits_only[2:]
            logger.debug(f"[PHONE_VALIDATE] Removed country code (91): {digits_only}")
        
        # Validate length
        if len(digits_only) != 10:
            error = f"Invalid phone: got {len(digits_only)} digits, need exactly 10. Input was: {phone_number}"
            logger.error(f"[PHONE_VALIDATE_ERROR] {error}")
            return None, error
        
        # Validate first digit (Indian numbers start with 6-9)
        if digits_only[0] not in ['6', '7', '8', '9']:
            error = f"Invalid phone: must start with 6-9. Got: {digits_only}"
            logger.error(f"[PHONE_VALIDATE_ERROR] {error}")
            return None, error
        
        logger.debug(f"[PHONE_VALIDATE_SUCCESS] Valid phone: {digits_only}")
        return digits_only, None
    
        """Get headers for Meritto API requests."""
        headers = {
            "secret-key": self.secret_key,
            "access-key": self.access_key,
            "Content-Type": "application/json"
        }
        logger.debug(f"[HEADERS] Using headers with keys: secret-key={self.secret_key[:10]}**, access-key={self.access_key[:10]}**")
        return headers
    
    async def send_lead(
        self,
        name: str,
        email: str,
        mobile: str,
        country_dial_code: str = "+91",
        entity_type: str = "inquiry",
        entity_id: Optional[int] = None,
        college_name: Optional[str] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Send a lead to Meritto CRM asynchronously with retry logic.
        
        Args:
            name: Customer/Inquirer name
            email: Customer email
            mobile: Customer mobile number
            country_dial_code: Country dial code (default: +91 for India)
            entity_type: Type of entity ('inquiry' or 'contact')
            entity_id: ID of the inquiry or contact record
            college_name: College name for context
            **kwargs: Additional fields to send
            
        Returns:
            Response from Meritto API or None if disabled/failed
        """
        logger.info(f"[NEW_LEAD_REQUEST] Starting lead sync - Name: {name}, Email: {email}, Mobile: {mobile}")
        
        if not self.is_enabled:
            logger.warning("[CONFIG] Meritto CRM is disabled (missing credentials). Lead NOT sent.")
            
            # Log to database that we skipped this
            if entity_id:
                self._log_to_database(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_email=email,
                    entity_name=name,
                    status="failed",
                    error_message="Meritto CRM not configured",
                    college_name=college_name
                )
            return None
        
        try:
            payload = {
                "name": name,
                "email": email,
                "country_dial_code": country_dial_code,
                "mobile": mobile,
                **kwargs
            }
            
            logger.debug(f"[PAYLOAD] Full payload: {json.dumps(payload, indent=2)}")
            
            url = f"{self.BASE_URL}{self.CREATE_LEAD_ENDPOINT}"
            logger.debug(f"[URL] Target endpoint: {url}")
            
            # Log initial attempt to database
            if entity_id:
                self._log_to_database(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_email=email,
                    entity_name=name,
                    status="pending",
                    college_name=college_name
                )
            
            # Use asyncio.to_thread to make HTTP call non-blocking with retry
            response = await self._send_with_retry(url, payload, entity_id, entity_type, email, name, college_name)
            
            if response:
                if entity_id:
                    self._log_to_database(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_email=email,
                        entity_name=name,
                        status="success",
                        response_data=response,
                        college_name=college_name,
                        attempt_count=1
                    )
                logger.info(f"[SUCCESS] Lead synced to Meritto - Name: {name}, Email: {email}, Response: {json.dumps(response)}")
                return response
            else:
                if entity_id:
                    self._log_to_database(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_email=email,
                        entity_name=name,
                        status="failed",
                        error_message="All retry attempts failed",
                        college_name=college_name,
                        attempt_count=self.MAX_RETRIES
                    )
                logger.error(f"[FAILED] All retry attempts failed for lead: {name} ({email})")
                return None
            
        except Exception as e:
            if entity_id:
                self._log_to_database(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_email=email,
                    entity_name=name,
                    status="failed",
                    error_message=str(e),
                    college_name=college_name
                )
            logger.exception(f"[EXCEPTION] Unexpected error sending lead {name} ({email}): {str(e)}")
            return None
    
    async def _send_with_retry(
        self,
        url: str,
        payload: Dict[str, Any],
        entity_id: Optional[int] = None,
        entity_type: str = "inquiry",
        entity_email: str = "",
        entity_name: str = "",
        college_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send request with exponential backoff retry logic.
        
        Args:
            url: API endpoint URL
            payload: Request payload
            entity_id: ID of inquiry/contact for logging
            entity_type: Type of entity
            entity_email: Email of entity
            entity_name: Name of entity
            college_name: College name
            
        Returns:
            Response from API or None if all retries fail
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.debug(f"[RETRY] Attempt {attempt}/{self.MAX_RETRIES}")
                
                response = await asyncio.to_thread(
                    self._make_request,
                    url,
                    payload
                )
                
                logger.debug(f"[RESPONSE] Success on attempt {attempt}: {json.dumps(response)}")
                return response
                
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                response_text = e.response.text
                logger.error(f"[HTTP_ERROR] Attempt {attempt}: Status {status_code} - {response_text}")
                
                # Don't retry on 401/403/404 (auth or not found errors)
                if status_code in [401, 403, 404]:
                    logger.error(f"[AUTH_ERROR] Response indicates authentication or permission issue. Stopping retries.")
                    # Log to database with error
                    if entity_id:
                        self._log_to_database(
                            entity_type=entity_type,
                            entity_id=entity_id,
                            entity_email=entity_email,
                            entity_name=entity_name,
                            status="failed",
                            error_message=f"HTTP {status_code}: {response_text}",
                            college_name=college_name,
                            attempt_count=attempt
                        )
                    return None
                
                if attempt < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"[WAIT] Waiting {wait_time}s before retry...")
                    # Log retrying status
                    if entity_id:
                        self._log_to_database(
                            entity_type=entity_type,
                            entity_id=entity_id,
                            entity_email=entity_email,
                            entity_name=entity_name,
                            status="retrying",
                            error_message=f"Attempt {attempt} failed with HTTP {status_code}, retrying...",
                            college_name=college_name,
                            attempt_count=attempt
                        )
                    await asyncio.sleep(wait_time)
            
            except httpx.ConnectError as e:
                logger.error(f"[CONNECT_ERROR] Attempt {attempt}: Connection failed - {str(e)}")
                if attempt < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY * (2 ** (attempt - 1))
                    logger.info(f"[WAIT] Waiting {wait_time}s before retry...")
                    if entity_id:
                        self._log_to_database(
                            entity_type=entity_type,
                            entity_id=entity_id,
                            entity_email=entity_email,
                            entity_name=entity_name,
                            status="retrying",
                            error_message=f"Attempt {attempt} connection failed, retrying...",
                            college_name=college_name,
                            attempt_count=attempt
                        )
                    await asyncio.sleep(wait_time)
            
            except httpx.TimeoutException as e:
                logger.error(f"[TIMEOUT] Attempt {attempt}: Request timed out - {str(e)}")
                if attempt < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY * (2 ** (attempt - 1))
                    logger.info(f"[WAIT] Waiting {wait_time}s before retry...")
                    if entity_id:
                        self._log_to_database(
                            entity_type=entity_type,
                            entity_id=entity_id,
                            entity_email=entity_email,
                            entity_name=entity_name,
                            status="retrying",
                            error_message=f"Attempt {attempt} timed out, retrying...",
                            college_name=college_name,
                            attempt_count=attempt
                        )
                    await asyncio.sleep(wait_time)
            
            except Exception as e:
                logger.exception(f"[EXCEPTION] Attempt {attempt}: Unexpected error - {str(e)}")
                if attempt < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY * (2 ** (attempt - 1))
                    logger.info(f"[WAIT] Waiting {wait_time}s before retry...")
                    if entity_id:
                        self._log_to_database(
                            entity_type=entity_type,
                            entity_id=entity_id,
                            entity_email=entity_email,
                            entity_name=entity_name,
                            status="retrying",
                            error_message=f"Attempt {attempt}: {str(e)}, retrying...",
                            college_name=college_name,
                            attempt_count=attempt
                        )
                    await asyncio.sleep(wait_time)
        
        logger.error(f"[FAILED] All {self.MAX_RETRIES} attempts exhausted for {url}")
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
            
        Raises:
            httpx.HTTPStatusError: If response status indicates error
            httpx.ConnectError: If connection fails
            httpx.TimeoutException: If request times out
        """
        logger.debug(f"[REQUEST] Sending POST request to {url}")
        logger.debug(f"[HEADERS] {json.dumps(dict(self._get_headers()), indent=2)}")
        
        with httpx.Client(timeout=self.REQUEST_TIMEOUT) as client:
            try:
                response = client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload
                )
                
                logger.debug(f"[RESPONSE_STATUS] HTTP {response.status_code}")
                logger.debug(f"[RESPONSE_BODY] {response.text}")
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"[HTTP_STATUS_ERROR] {e.response.status_code}: {e.response.text}")
                raise
            except httpx.ConnectError as e:
                logger.error(f"[CONNECT_ERROR] Failed to connect to Meritto API: {str(e)}")
                raise
            except httpx.TimeoutException as e:
                logger.error(f"[TIMEOUT_ERROR] Request timed out after {self.REQUEST_TIMEOUT}s: {str(e)}")
                raise
            except Exception as e:
                logger.exception(f"[REQUEST_ERROR] Unexpected error during request: {str(e)}")
                raise
    
    async def send_inquiry_to_crm(
        self,
        inquiry_id: int,
        name: str,
        email: str,
        phone_number: str,
        course_interested: Optional[str] = None,
        message: Optional[str] = None,
        college_name: Optional[str] = None,
        c_course: Optional[str] = None,
        c_specialization: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send an inquiry submission to Meritto CRM.
        
        Args:
            inquiry_id: ID of the inquiry record
            name: Inquirer name
            email: Inquirer email
            phone_number: Inquirer phone number (10 digits for India)
            course_interested: Course name they're interested in
            message: Inquiry message
            college_name: College name for context
            
        Returns:
            Response from API or None if failed
        """
        logger.info(f"[INQUIRY] Processing inquiry submission - {name} from {college_name}")
        
        # Validate phone number first
        phone_clean, phone_error = self._validate_and_clean_phone(phone_number)
        if phone_error:
            logger.error(f"[INQUIRY_PHONE_ERROR] {phone_error}")
            self._log_to_database(
                entity_type="inquiry",
                entity_id=inquiry_id,
                entity_email=email,
                entity_name=name,
                status="failed",
                error_message=f"Phone validation failed: {phone_error}",
                college_name=college_name
            )
            return None
        
        extra_fields = {}
        
        if course_interested:
            extra_fields["course"] = course_interested
            logger.debug(f"[INQUIRY] Course: {course_interested}")
        
        if message:
            extra_fields["message"] = message
            logger.debug(f"[INQUIRY] Message length: {len(message)} chars")
        
        if c_course:
            extra_fields["c_course"] = c_course
            logger.debug(f"[INQUIRY] C Course: {c_course}")
        
        if c_specialization:
            extra_fields["c_specialization"] = c_specialization
            logger.debug(f"[INQUIRY] C Specialization: {c_specialization}")
        
        result = await self.send_lead(
            name=name,
            email=email,
            mobile=phone_clean,
            country_dial_code="+91",
            entity_type="inquiry",
            entity_id=inquiry_id,
            college_name=college_name,
            **extra_fields
        )
        
        if result:
            logger.info(f"[INQUIRY_SUCCESS] Inquiry synced for {email}")
        else:
            logger.error(f"[INQUIRY_FAILED] Failed to sync inquiry for {email}")
        
        return result
    
    async def send_contact_to_crm(
        self,
        contact_id: int,
        name: str,
        email: str,
        phone_no: str,
        state: Optional[str] = None,
        city: Optional[str] = None,
        address: Optional[str] = None,
        message: Optional[str] = None,
        college_name: Optional[str] = None,
        c_course: Optional[str] = None,
        c_specialization: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a contact form submission to Meritto CRM.
        
        Args:
            contact_id: ID of the contact record
            name: Contact name
            email: Contact email
            phone_no: Contact phone number (10 digits for India)
            state: Contact state
            city: Contact city
            address: Contact address
            message: Contact message
            college_name: College name for context
            
        Returns:
            Response from API or None if failed
        """
        logger.info(f"[CONTACT] Processing contact form - {name} from {college_name}")
        
        # Validate phone number first
        phone_clean, phone_error = self._validate_and_clean_phone(phone_no)
        if phone_error:
            logger.error(f"[CONTACT_PHONE_ERROR] {phone_error}")
            self._log_to_database(
                entity_type="contact",
                entity_id=contact_id,
                entity_email=email,
                entity_name=name,
                status="failed",
                error_message=f"Phone validation failed: {phone_error}",
                college_name=college_name
            )
            return None
        
        extra_fields = {}
        
        if state:
            extra_fields["state"] = state
            logger.debug(f"[CONTACT] State: {state}")
        
        if city:
            extra_fields["city"] = city
            logger.debug(f"[CONTACT] City: {city}")
        
        if address:
            extra_fields["address"] = address
            logger.debug(f"[CONTACT] Address: {address}")
        
        if message:
            extra_fields["inquiry"] = message
            logger.debug(f"[CONTACT] Message length: {len(message)} chars")
        
        if c_course:
            extra_fields["c_course"] = c_course
            logger.debug(f"[CONTACT] C Course: {c_course}")
        
        if c_specialization:
            extra_fields["c_specialization"] = c_specialization
            logger.debug(f"[CONTACT] C Specialization: {c_specialization}")
        
        result = await self.send_lead(
            name=name,
            email=email,
            mobile=phone_clean,
            country_dial_code="+91",
            entity_type="contact",
            entity_id=contact_id,
            college_name=college_name,
            **extra_fields
        )
        
        if result:
            logger.info(f"[CONTACT_SUCCESS] Contact form synced for {email}")
        else:
            logger.error(f"[CONTACT_FAILED] Failed to sync contact form for {email}")
        
        return result


# Global instance
meritto_service = MeritoCRMService()
