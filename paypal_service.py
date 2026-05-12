"""
PayPal REST API Integration Service
Handles PayPal order creation, capture, and payment tracking
Production-ready with proper error handling and logging
"""

import os
import requests
import json
from typing import Dict, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class PayPalService:
    """
    Service class to interact with PayPal REST API (Sandbox/Production)
    """
    
    def __init__(self):
        self.client_id = os.getenv("PAYPAL_CLIENT_ID", "YOUR_SANDBOX_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "YOUR_SANDBOX_CLIENT_SECRET")
        self.environment = os.getenv("PAYPAL_ENVIRONMENT", "sandbox")  # sandbox or production
        
        if self.environment == "production":
            self.base_url = "https://api-m.paypal.com"
        else:
            self.base_url = "https://api-m.sandbox.paypal.com"
        
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self) -> Optional[str]:
        """
        Get OAuth access token from PayPal
        Tokens are cached until expiry
        """
        # Return cached token if still valid
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        auth = (self.client_id, self.client_secret)
        headers = {"Accept": "application/json", "Accept-Language": "en_US"}
        data = {"grant_type": "client_credentials"}
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=auth,
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            self.access_token = result["access_token"]
            
            # Cache for expires_in seconds (typically 3600)
            from datetime import timedelta
            self.token_expiry = datetime.now() + timedelta(seconds=result.get("expires_in", 3600) - 60)
            
            return self.access_token
        except requests.exceptions.RequestException as e:
            print(f"Failed to get PayPal access token: {str(e)}")
            return None
    
    def create_order(
        self,
        amount: str,
        currency: str = "USD",
        reference_id: str = None,
        description: str = None,
        return_url: str = None,
        cancel_url: str = None
    ) -> Tuple[bool, Dict]:
        """
        Create a PayPal order
        Returns (success: bool, response_data: dict)
        """
        access_token = self.get_access_token()
        if not access_token:
            return False, {"error": "Failed to authenticate with PayPal"}
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        # Prepare order payload
        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference_id or f"order-{datetime.now().timestamp()}",
                    "description": description or "Service Payment",
                    "amount": {
                        "currency_code": currency.upper(),
                        "value": str(amount)
                    }
                }
            ],
            "application_context": {
                "brand_name": "Akagera Inc",
                "locale": "en-US",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
                "return_url": return_url or "http://localhost:3000/payment-success",
                "cancel_url": cancel_url or "http://localhost:3000/payment-cancel"
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders",
                headers=headers,
                json=order_data,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return True, result
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            try:
                error_msg = e.response.json() if e.response else str(e)
            except:
                pass
            print(f"Failed to create PayPal order: {error_msg}")
            return False, {"error": error_msg}
    
    def capture_order(self, order_id: str) -> Tuple[bool, Dict]:
        """
        Capture (complete) a PayPal order
        Must be called after user approves the order on PayPal
        Returns (success: bool, response_data: dict)
        """
        access_token = self.get_access_token()
        if not access_token:
            return False, {"error": "Failed to authenticate with PayPal"}
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return True, result
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            try:
                error_msg = e.response.json() if e.response else str(e)
            except:
                pass
            print(f"Failed to capture PayPal order: {error_msg}")
            return False, {"error": error_msg}
    
    def get_order_details(self, order_id: str) -> Tuple[bool, Dict]:
        """
        Get details of a PayPal order
        """
        access_token = self.get_access_token()
        if not access_token:
            return False, {"error": "Failed to authenticate with PayPal"}
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/v2/checkout/orders/{order_id}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return True, result
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            try:
                error_msg = e.response.json() if e.response else str(e)
            except:
                pass
            print(f"Failed to get PayPal order details: {error_msg}")
            return False, {"error": error_msg}


# Initialize PayPal service
paypal_service = PayPalService()
