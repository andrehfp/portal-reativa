#!/usr/bin/env python3

import sys
import requests
import time
from urllib.parse import quote

def test_sql_injection_protection():
    """Test SQL injection protection"""
    print("=== Testing SQL Injection Protection ===")
    
    base_url = "http://localhost:8000"
    
    # Test malicious sort parameter
    malicious_sorts = [
        "price; DROP TABLE properties; --",
        "price UNION SELECT * FROM properties",
        "1' OR '1'='1",
        "price DESC; DELETE FROM properties; --"
    ]
    
    for malicious_sort in malicious_sorts:
        try:
            response = requests.get(f"{base_url}/search", params={
                'q': 'apartamento',
                'sort': malicious_sort
            }, timeout=5)
            
            if response.status_code == 400:
                print(f"✅ SQL injection blocked: {malicious_sort[:30]}...")
            else:
                print(f"⚠️  Potential vulnerability: {malicious_sort[:30]}... (Status: {response.status_code})")
        except Exception as e:
            print(f"❌ Error testing SQL injection: {e}")

def test_xss_protection():
    """Test XSS protection"""
    print("\n=== Testing XSS Protection ===")
    
    base_url = "http://localhost:8000"
    
    # Test malicious search queries
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "'\"><script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>"
    ]
    
    for payload in xss_payloads:
        try:
            response = requests.get(f"{base_url}/search", params={
                'q': payload,
                'page': 1,
                'sort': 'relevance'
            }, timeout=5)
            
            if response.status_code == 400:
                print(f"✅ XSS blocked: {payload[:30]}...")
            elif "<script>" not in response.text.lower() and "javascript:" not in response.text.lower():
                print(f"✅ XSS escaped: {payload[:30]}...")
            else:
                print(f"❌ XSS vulnerability: {payload[:30]}...")
        except Exception as e:
            print(f"❌ Error testing XSS: {e}")

def test_input_validation():
    """Test input validation"""
    print("\n=== Testing Input Validation ===")
    
    base_url = "http://localhost:8000"
    
    # Test invalid parameters
    test_cases = [
        {'q': 'a' * 300, 'expected': 400},  # Query too long
        {'page': 0, 'expected': 422},       # Invalid page
        {'page': 9999, 'expected': 422},    # Page too high
        {'sort': 'invalid_sort', 'expected': 200},  # Invalid sort (should default)
    ]
    
    for case in test_cases:
        try:
            response = requests.get(f"{base_url}/search", params=case, timeout=5)
            
            if 'expected' in case:
                if response.status_code == case['expected']:
                    print(f"✅ Input validation working: {str(case)[:50]}...")
                else:
                    print(f"⚠️  Unexpected response: {str(case)[:50]}... (Status: {response.status_code})")
            
        except Exception as e:
            print(f"❌ Error testing input validation: {e}")

def test_rate_limiting():
    """Test rate limiting"""
    print("\n=== Testing Rate Limiting ===")
    
    base_url = "http://localhost:8000"
    
    print("Making rapid requests to test rate limiting...")
    blocked_count = 0
    success_count = 0
    
    for i in range(5):  # Make 5 quick requests
        try:
            response = requests.get(f"{base_url}/search", params={
                'q': f'test{i}',
                'page': 1,
                'sort': 'relevance'
            }, timeout=5)
            
            if response.status_code == 429:
                blocked_count += 1
            elif response.status_code == 200:
                success_count += 1
                
        except Exception as e:
            print(f"Error in rate limit test: {e}")
        
        time.sleep(0.1)  # Small delay between requests
    
    print(f"Success: {success_count}, Rate limited: {blocked_count}")
    if success_count > 0:
        print("✅ Normal requests working")
    if blocked_count > 0:
        print("✅ Rate limiting active")
    else:
        print("ℹ️  Rate limiting may need more requests to trigger (30/minute)")

def test_security_headers():
    """Test security headers"""
    print("\n=== Testing Security Headers ===")
    
    base_url = "http://localhost:8000"
    
    try:
        response = requests.get(f"{base_url}/search?q=test", timeout=5)
        
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy"
        ]
        
        for header in security_headers:
            if header in response.headers:
                print(f"✅ {header}: {response.headers[header]}")
            else:
                print(f"❌ Missing: {header}")
                
    except Exception as e:
        print(f"❌ Error testing headers: {e}")

def test_error_handling():
    """Test that errors don't expose sensitive information"""
    print("\n=== Testing Error Handling ===")
    
    base_url = "http://localhost:8000"
    
    # Test various error conditions
    error_tests = [
        {'path': '/search', 'params': {'q': '\\' * 100}, 'desc': 'Invalid characters'},
        {'path': '/property/99999', 'params': {}, 'desc': 'Non-existent property'},
    ]
    
    for test in error_tests:
        try:
            if test['params']:
                response = requests.get(f"{base_url}{test['path']}", params=test['params'], timeout=5)
            else:
                response = requests.get(f"{base_url}{test['path']}", timeout=5)
            
            # Check if response contains sensitive information
            sensitive_terms = ['sqlite', 'database', 'traceback', 'exception', 'file path']
            has_sensitive_info = any(term in response.text.lower() for term in sensitive_terms)
            
            if has_sensitive_info:
                print(f"⚠️  {test['desc']}: May expose sensitive information")
            else:
                print(f"✅ {test['desc']}: No sensitive information exposed")
                
        except Exception as e:
            print(f"❌ Error testing {test['desc']}: {e}")

if __name__ == "__main__":
    print("🔒 Security Testing Suite for Portal Reativa")
    print("=" * 50)
    
    # Note: These tests require the server to be running on localhost:8001
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running, starting security tests...\n")
        else:
            print("❌ Server responded with error, tests may not be accurate")
    except:
        print("❌ Server not accessible at http://localhost:8000")
        print("Please start the server with: python main.py")
        sys.exit(1)
    
    test_sql_injection_protection()
    test_xss_protection()
    test_input_validation()
    test_rate_limiting()
    test_security_headers()
    test_error_handling()
    
    print("\n🔒 Security testing completed!")
    print("Review any warnings above and ensure all critical issues are resolved.")