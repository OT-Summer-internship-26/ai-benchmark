#!/usr/bin/env python3
"""Extract the FULL certificate chain from api.groq.com."""

import ssl
import socket
import certifi
from OpenSSL import SSL, crypto

print("🔗 Extracting full certificate chain from api.groq.com...\n")

try:
    # Create SSL context to get chain
    context = ssl.create_default_context()
    with socket.create_connection(('api.groq.com', 443), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname='api.groq.com') as ssock:
            # Get peer certificate
            cert_der = ssock.getpeercert(binary_form=True)
            cert = crypto.load_certificate(crypto.FILETYPE_ASN1, cert_der)
            
            print(f"✅ Server Certificate:")
            print(f"   Subject: {cert.get_subject()}")
            print(f"   Issuer: {cert.get_issuer()}")
            print()
            
            # Try to get certificate chain from peer verification info
            # Unfortunately, Python's ssl module doesn't expose the full chain
            # But we can try openssl command if available
            
    # Alternative: Use openssl command to get full chain
    print(f"Attempting to extract chain with openssl...")
    import subprocess
    
    try:
        # Use openssl to get the full chain
        result = subprocess.run(
            ['openssl', 's_client', '-connect', 'api.groq.com:443', '-showcerts'],
            input=b'',
            capture_output=True,
            timeout=10
        )
        
        output = result.stdout.decode('utf-8', errors='ignore')
        
        # Extract certificates from output
        certs = []
        in_cert = False
        current_cert = []
        
        for line in output.split('\n'):
            if '-----BEGIN CERTIFICATE-----' in line:
                in_cert = True
                current_cert = [line]
            elif '-----END CERTIFICATE-----' in line:
                current_cert.append(line)
                certs.append('\n'.join(current_cert))
                current_cert = []
                in_cert = False
            elif in_cert:
                current_cert.append(line)
        
        print(f"✅ Found {len(certs)} certificate(s) in chain")
        
        # Append all to certifi
        certifi_path = certifi.where()
        with open(certifi_path, 'a') as f:
            f.write("\n# Full certificate chain for api.groq.com (Avast MITM inspection)\n")
            for i, cert in enumerate(certs):
                f.write(f"\n# Certificate {i+1}\n")
                f.write(cert)
                f.write("\n")
        
        print(f"✅ Added full certificate chain to {certifi_path}")
        
    except FileNotFoundError:
        print("❌ openssl command not found - trying alternative method...")
        
        # Alternative: Use pyOpenSSL if available
        try:
            from OpenSSL import SSL, crypto
            
            context = SSL.Context(SSL.TLS_CLIENT_METHOD)
            conn = SSL.Connection(context, socket.socket())
            conn.connect(('api.groq.com', 443))
            conn.do_handshake()
            
            # Get the peer certificate chain
            cert_chain = conn.get_peer_cert_chain()
            print(f"✅ Found {len(cert_chain)} certificate(s) in chain")
            
            certifi_path = certifi.where()
            with open(certifi_path, 'a') as f:
                f.write("\n# Full certificate chain for api.groq.com\n")
                for i, cert in enumerate(cert_chain):
                    f.write(f"\n# Certificate {i+1}\n")
                    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode())
            
            print(f"✅ Added full certificate chain to {certifi_path}")
            conn.close()
            
        except Exception as e:
            print(f"❌ Failed to get chain: {e}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
