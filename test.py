import onetimepass
import base64
import secrets
import time
import qrcode

# Secret key
key = base64.b32encode(secrets.token_bytes(10)).decode('utf-8')

# Generate OTP Auth URL for Google Authenticator
issuer = "MyApp"
account_name = "user@example.com"
otpauth_url = f"otpauth://totp/{issuer}:{account_name}?secret={key}&issuer={issuer}"

# Generate QR code
qr = qrcode.make(otpauth_url)
qr.show()

# Print key
print("Key:", key)

# Generate OTP
for i in range(19):
    otp = onetimepass.get_totp(key)
    print("OTP:", otp)
    time.sleep(5)