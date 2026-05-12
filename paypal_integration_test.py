"""
PayPal Integration - Quick Testing Guide
Test all PayPal endpoints locally

Usage:
    python paypal_integration_test.py --user-id 1 --service-id 1 --amount 99.99
"""

import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000/api"
SANDBOX_MODE = True

class PayPalIntegrationTester:
    def __init__(self, user_id, service_id, amount):
        self.user_id = user_id
        self.service_id = service_id
        self.amount = amount
        self.paypal_order_id = None
        self.payment_id = None
        
    def print_header(self, title):
        print("\n" + "="*70)
        print(f"  {title}")
        print("="*70)
    
    def print_response(self, response, label):
        print(f"\n{label}:")
        print(f"Status Code: {response.status_code}")
        try:
            print("Response Body:")
            print(json.dumps(response.json(), indent=2))
        except:
            print(f"Response Text: {response.text}")
    
    def test_create_order(self):
        """Test creating a PayPal order"""
        self.print_header("TEST 1: Create PayPal Order")
        
        url = f"{API_BASE_URL}/payments/paypal/create-order"
        params = {"user_id": self.user_id}
        payload = {
            "amount": self.amount,
            "service_id": self.service_id,
            "currency": "USD"
        }
        
        print(f"POST {url}")
        print(f"Params: {params}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, params=params)
            self.print_response(response, "Response")
            
            if response.status_code == 200:
                data = response.json()
                self.paypal_order_id = data.get('paypal_order_id')
                print(f"\n✅ SUCCESS: Order created")
                print(f"   PayPal Order ID: {self.paypal_order_id}")
                print(f"   Approval URL: {data.get('approval_url')}")
                return True
            else:
                print(f"\n❌ FAILED: Status {response.status_code}")
                return False
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            return False
    
    def test_capture_order(self):
        """Test capturing a PayPal order"""
        self.print_header("TEST 2: Capture PayPal Order")
        
        if not self.paypal_order_id:
            print("❌ SKIPPED: No PayPal Order ID from previous test")
            return False
        
        url = f"{API_BASE_URL}/payments/paypal/capture-order"
        params = {
            "paypal_order_id": self.paypal_order_id,
            "user_id": self.user_id
        }
        
        print(f"POST {url}")
        print(f"Params: {params}")
        print("\nNote: This would complete the payment on PayPal's server")
        
        try:
            response = requests.post(url, params=params)
            self.print_response(response, "Response")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ SUCCESS: Order captured")
                print(f"   Status: {data.get('status')}")
                print(f"   Payment ID: {data.get('payment_id')}")
                return True
            else:
                print(f"\n❌ FAILED: Status {response.status_code}")
                return False
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            return False
    
    def test_get_order_details(self):
        """Test getting PayPal order details"""
        self.print_header("TEST 3: Get Order Details")
        
        if not self.paypal_order_id:
            print("❌ SKIPPED: No PayPal Order ID from previous test")
            return False
        
        url = f"{API_BASE_URL}/payments/paypal/details/{self.paypal_order_id}"
        params = {"user_id": self.user_id}
        
        print(f"GET {url}")
        print(f"Params: {params}")
        
        try:
            response = requests.get(url, params=params)
            self.print_response(response, "Response")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ SUCCESS: Order details retrieved")
                print(f"   Payment Status: {data.get('payment_status')}")
                return True
            else:
                print(f"\n❌ FAILED: Status {response.status_code}")
                return False
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            return False
    
    def test_get_user_payments(self):
        """Test getting user's payment history"""
        self.print_header("TEST 4: Get User Payment History")
        
        url = f"{API_BASE_URL}/payments/user/{self.user_id}"
        
        print(f"GET {url}")
        
        try:
            response = requests.get(url)
            self.print_response(response, "Response")
            
            if response.status_code == 200:
                payments = response.json()
                print(f"\n✅ SUCCESS: Retrieved {len(payments)} payments")
                
                # Filter PayPal payments
                paypal_payments = [p for p in payments if p.get('payment_method') == 'paypal']
                print(f"   PayPal Payments: {len(paypal_payments)}")
                print(f"   Other Payments: {len(payments) - len(paypal_payments)}")
                
                return True
            else:
                print(f"\n❌ FAILED: Status {response.status_code}")
                return False
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            return False
    
    def test_health_check(self):
        """Test API health"""
        self.print_header("TEST 0: API Health Check")
        
        url = f"{API_BASE_URL.replace('/api', '')}/health"
        
        print(f"GET {url}")
        
        try:
            response = requests.get(url)
            self.print_response(response, "Response")
            
            if response.status_code == 200:
                print(f"\n✅ SUCCESS: API is healthy")
                return True
            else:
                print(f"\n❌ FAILED: Status {response.status_code}")
                return False
        except Exception as e:
            print(f"\n❌ ERROR: API unreachable - {str(e)}")
            print("Make sure backend is running: python -m uvicorn main:app --reload")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        self.print_header("PAYPAL INTEGRATION TEST SUITE")
        print(f"Started at: {datetime.now()}")
        print(f"User ID: {self.user_id}")
        print(f"Service ID: {self.service_id}")
        print(f"Amount: ${self.amount}")
        print(f"Environment: {'SANDBOX' if SANDBOX_MODE else 'PRODUCTION'}")
        
        results = {}
        
        # Run tests
        results['health_check'] = self.test_health_check()
        
        if results['health_check']:
            results['create_order'] = self.test_create_order()
            results['get_details'] = self.test_get_order_details()
            # Don't auto-run capture in tests - it's a destructive operation
            # results['capture_order'] = self.test_capture_order()
            results['user_payments'] = self.test_get_user_payments()
        
        # Print summary
        self.print_header("TEST SUMMARY")
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, passed_flag in results.items():
            status = "✅ PASS" if passed_flag else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        print(f"Ended at: {datetime.now()}")
        
        return passed == total


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='PayPal Integration Tester')
    parser.add_argument('--user-id', type=int, default=1, help='User ID (default: 1)')
    parser.add_argument('--service-id', type=int, default=1, help='Service ID (default: 1)')
    parser.add_argument('--amount', type=float, default=99.99, help='Payment amount (default: 99.99)')
    parser.add_argument('--api-url', type=str, default=API_BASE_URL, help='API base URL')
    
    args = parser.parse_args()
    
    # Update API URL if provided
    global API_BASE_URL
    API_BASE_URL = args.api_url
    
    tester = PayPalIntegrationTester(args.user_id, args.service_id, args.amount)
    success = tester.run_all_tests()
    
    exit(0 if success else 1)


if __name__ == '__main__':
    main()
