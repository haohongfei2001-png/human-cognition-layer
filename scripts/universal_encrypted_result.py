"""Authenticated result envelope. Public recipient only in CI; private key stays local."""
import base64,hashlib,json,os
from pathlib import Path
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding,rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SCHEMA='hcl-private-development-result-v1'

def recipient_fingerprint(public):
    key=serialization.load_pem_public_key(public)
    if not isinstance(key,rsa.RSAPublicKey)or key.key_size<3072:raise ValueError('RSA3072_OR_STRONGER_PUBLIC_RECIPIENT_REQUIRED')
    return hashlib.sha256(key.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()

def encrypt_result(plaintext,public,package_sha256):
    if not isinstance(plaintext,bytes)or len(plaintext)>16*1024*1024:raise ValueError('BOUNDED_RESULT_REQUIRED')
    fingerprint=recipient_fingerprint(public)
    if not isinstance(package_sha256,str)or len(package_sha256)!=64 or any(c not in '0123456789abcdef'for c in package_sha256):raise ValueError('FROZEN_PACKAGE_ID_REQUIRED')
    header=dict(schema=SCHEMA,algorithm='RSA-OAEP-SHA256+AES-256-GCM',recipient_sha256=fingerprint,package_sha256=package_sha256)
    aad=json.dumps(header,sort_keys=True,separators=(',',':')).encode();key=os.urandom(32);nonce=os.urandom(12)
    encrypted=AESGCM(key).encrypt(nonce,plaintext,aad)
    public_key=serialization.load_pem_public_key(public)
    wrapped=public_key.encrypt(key,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    return dict(header,nonce_b64=base64.b64encode(nonce).decode(),wrapped_key_b64=base64.b64encode(wrapped).decode(),ciphertext_b64=base64.b64encode(encrypted).decode())

def decrypt_result(envelope,private,expected_package):
    if set(envelope)!={'schema','algorithm','recipient_sha256','package_sha256','nonce_b64','wrapped_key_b64','ciphertext_b64'}or envelope['schema']!=SCHEMA or envelope['algorithm']!='RSA-OAEP-SHA256+AES-256-GCM'or envelope['package_sha256']!=expected_package:
        raise ValueError('ENVELOPE_IDENTITY_MISMATCH')
    private_key=serialization.load_pem_private_key(private,password=None)
    public=private_key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    if recipient_fingerprint(public)!=envelope['recipient_sha256']:raise ValueError('WRONG_RECIPIENT')
    header={k:envelope[k]for k in ('schema','algorithm','recipient_sha256','package_sha256')}
    aad=json.dumps(header,sort_keys=True,separators=(',',':')).encode()
    key=private_key.decrypt(base64.b64decode(envelope['wrapped_key_b64'],validate=True),padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    return AESGCM(key).decrypt(base64.b64decode(envelope['nonce_b64'],validate=True),base64.b64decode(envelope['ciphertext_b64'],validate=True),aad)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',required=True);parser.add_argument('--public-key',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    plaintext=Path(args.receipt).read_bytes();value=json.loads(plaintext)
    envelope=encrypt_result(plaintext,Path(args.public_key).read_bytes(),value['package_sha256'])
    Path(args.output).write_text(json.dumps(envelope,sort_keys=True)+'\n')
    print('ENCRYPTED_RESULT_READY; PLAINTEXT_NOT_UPLOADED')
