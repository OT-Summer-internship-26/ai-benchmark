#!/usr/bin/env python3
"""Test basic HTTPS connectivity."""

import sys
import os
import certifi
import ssl
import urllib.request
import socket

os.environ['SSL_CERT_FILE'] = certifi.where()

print("🔧 Testing HTTPS connectivity...\n")

# Test 1: Basic HTTPS to a reliable server
print("Test 1: HTTPS to httpbin.org")
try:
    with urllib.request.urlopen('https://httpbin.org/status/200', timeout=10) as response:
        print(f"   ✅ SUCCESS: Status {response.status}")
except Exception as e:
    print(f"   ❌ FAILED: {type(e).__name__}: {e}")

# Test 2: HTTPS to Google
print("\nTest 2: HTTPS to Google")
try:
    with urllib.request.urlopen('https://www.google.com', timeout=10) as response:
        print(f"   ✅ SUCCESS: Status {response.status}")
except Exception as e:
    print(f"   ❌ FAILED: {type(e).__name__}: {e}")

# Test 3: Try to connect to Groq API endpoint
print("\nTest 3: Check network connectivity to api.groq.com")
try:
    sock = socket.create_connection(('api.groq.com', 443), timeout=10)
    print(f"   ✅ Socket connection successful to api.groq.com:443")
    sock.close()
except Exception as e:
    print(f"   ❌ Socket connection failed: {type(e).__name__}: {e}")

# Test 4: Try TLS handshake to api.groq.com
print("\nTest 4: TLS handshake to api.groq.com")
try:
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(certifi.where())
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        with context.wrap_socket(sock, server_hostname='api.groq.com') as ssock:
            ssock.connect(('api.groq.com', 443))
            print(f"   ✅ TLS handshake successful")
            print(f"   Server certificate: {ssock.getpeercert()}")
except Exception as e:
    print(f"   ❌ TLS handshake failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Summary: If tests 1-2 pass, HTTPS/SSL is working.")
print("If test 3 fails, api.groq.com is not reachable (network/firewall).")
print("If test 4 fails, TLS certificate verification has issues.")
