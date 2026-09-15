import os

# Sanitize SSL_CERT_FILE on Windows if Anaconda sets it to a non-existent path
ssl_cert = os.environ.get("SSL_CERT_FILE")
if ssl_cert and not os.path.exists(ssl_cert):
    os.environ.pop("SSL_CERT_FILE", None)
