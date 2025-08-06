from ecdsa import SigningKey, VerifyingKey, NIST384p

# Generate Key
sk = SigningKey.generate(curve=NIST384p)
vk = sk.get_verifying_key()

open("director_private.pem", "wb").write(sk.to_pem())
open("director_public.pem", "wb").write(vk.to_pem())

# Make Signature
sk = SigningKey.from_pem(open("director_private.pem").read())
message = open("./message.txt", "rb").read()
# signature = sk.sign("message1".encode())
sig = sk.sign(message)
open("signature", "wb").write(sig)

# Verifying
# assert vk.verify(signature, "message1".encode())

sig = open("./signature", "rb").read()

try:
    # print(vk.verify(signature, "message2".encode()))
    print(vk.verify(sig, message))
    print("Verify Success")
except Exception as e:
    print("Verify Fault")