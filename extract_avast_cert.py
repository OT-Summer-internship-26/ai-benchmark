#!/usr/bin/env python3
"""Extract Avast certificate and add it to certifi bundle."""

import ssl
import os
import certifi
from pathlib import Path

print("🔍 Extracting Avast SSL certificate from api.groq.com...\n")

try:
    # Get the server certificate
    context = ssl.create_default_context()
    with ssl.create_connection(('api.groq.com', 443), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname='api.groq.com') as ssock:
            cert_der = ssock.getpeercert(binary_form=True)
            
    # Convert DER to PEM
    import base64
    pem_lines = [
        "-----BEGIN CERTIFICATE-----",
        base64.b64encode(cert_der).decode().strip(),
        "-----END CERTIFICATE-----"
    ]
    pem_cert = "\n".join(pem_lines)
    
    # Get certifi path and add to it
    certifi_path = certifi.where()
    print(f"✅ Got server certificate from api.groq.com")
    print(f"✅ Certifi bundle: {certifi_path}\n")
    
    # Read current certifi
    with open(certifi_path, 'r') as f:
        current_content = f.read()
    
    # Append Avast cert if not already there
    if "Avast Web/Mail Shield" not in current_content:
        with open(certifi_path, 'a') as f:
            f.write("\n# Added Avast Web/Mail Shield certificate for MITM inspection\n")
            f.write(pem_cert)
            f.write("\n")
        print(f"✅ Added Avast certificate to certifi bundle")
    else:
        print(f"ℹ️  Avast certificate already in certifi bundle")
        
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
