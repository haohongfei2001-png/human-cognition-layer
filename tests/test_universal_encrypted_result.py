import json,unittest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from scripts.universal_encrypted_result import encrypt_result,decrypt_result

class EncryptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        cls.private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
        cls.public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    def test_roundtrip_is_private_and_package_bound(self):
        raw=b'SYNTHETIC_PRIVATE_OUTPUT_CANARY';package='a'*64
        envelope=encrypt_result(raw,self.public,package)
        self.assertNotIn(raw.decode(),json.dumps(envelope));self.assertNotIn('PRIVATE KEY',json.dumps(envelope))
        self.assertEqual(decrypt_result(envelope,self.private,package),raw)
        with self.assertRaises(ValueError):decrypt_result(envelope,self.private,'b'*64)
    def test_ciphertext_and_header_tampering_rejected(self):
        envelope=encrypt_result(b'private synthetic result',self.public,'a'*64)
        for changed in [dict(envelope,recipient_sha256='0'*64),dict(envelope,ciphertext_b64=('B' if envelope['ciphertext_b64'][0]=='A' else 'A')+envelope['ciphertext_b64'][1:])]:
            with self.assertRaises(Exception):decrypt_result(changed,self.private,'a'*64)
