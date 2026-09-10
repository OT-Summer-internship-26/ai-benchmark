#!/usr/bin/env python3
"""Extract certificate chain using pyOpenSSL."""

import socket
import ssl
import certifi
from OpenSSL import SSL, crypto

print("🔗 Extracting full certificate chain from api.groq.com...\n")

try:
    # Use pyOpenSSL to get the cert chain
    context = SSL.Context(SSL.TLS_CLIENT_METHOD)
    context.set_verify(SSL.VERIFY_NONE, lambda *args: True)  # Don't verify yet
    
    conn = SSL.Connection(context, socket.socket())
    conn.connect(('api.groq.com', 443))
    conn.do_handshake()
    
    # Get certificate chain
    cert_chain = conn.get_peer_cert_chain()
    print(f"✅ Got certificate chain with {len(cert_chain)} certificate(s)\n")
    
    # Display chain
    for i, cert in enumerate(cert_chain):
        subject = cert.get_subject()
        issuer = cert.get_issuer()
        print(f"Cert {i+1}:")
        print(f"  Subject: {subject}")
        print(f"  Issuer: {issuer}")
        print()
    
    # Append entire chain to certifi
    certifi_path = certifi.where()
    print(f"Appending chain to: {certifi_path}\n")
    
    with open(certifi_path, 'a') as f:
        f.write("\n# Full certificate chain for api.groq.com (Avast MITM inspection)\n")
        f.write("# Added to support corporate SSL inspection\n")
        for i, cert in enumerate(cert_chain):
            f.write(f"\n# Certificate {i+1}\n")
            pem_data = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode()
            f.write(pem_data)
    
    print(f"✅ Successfully appended {len(cert_chain)} certificate(s) to certifi bundle")
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
