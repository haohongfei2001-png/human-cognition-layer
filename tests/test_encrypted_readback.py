"""Synthetic private keys are memory-only fixtures, never user custody evidence."""
import base64,contextlib,copy,io,json,os,stat,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from scripts.universal_encrypted_result import encrypt_result,recipient_fingerprint
from scripts import verify_encrypted_readback as r

class ReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        cls.private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
        cls.public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        other=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        cls.other=other.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    def setUp(self):
        self.receipt=json.dumps(dict(package_sha256='a'*64,raw_answer='SYNTHETIC_PRIVATE_ANSWER_CANARY')).encode()
        self.envelope=encrypt_result(self.receipt,self.public,'a'*64)
        self.expected=dict(schema='hcl-encrypted-readback-expectations-v1',repository='owner/repo',
            artifact_id=100,artifact_name='encrypted-200',run_id=200,head_sha='b'*40,archive_sha256='c'*64,
            member_name='receipt.enc.json',package_sha256='a'*64,recipient_sha256=recipient_fingerprint(self.public),receipt_sha256=r.sha256(self.receipt))
        url='https://api.github.com/repos/owner/repo/actions/artifacts/100'
        self.metadata=dict(id=100,name='encrypted-200',url=url,archive_download_url=url+'/zip',workflow_run=dict(id=200,head_sha='b'*40))
        self.archive=self.zip_bytes();self.rehash()
    def zip_bytes(self,rows=None):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED)as bundle:
            for name,raw in rows or [('receipt.enc.json',json.dumps(self.envelope))]:bundle.writestr(name,raw)
        return buffer.getvalue()
    def rehash(self):
        self.expected['archive_sha256']=r.sha256(self.archive);self.metadata['digest']='sha256:'+self.expected['archive_sha256']
    def inspect(self):return r.inspect_archive(self.archive,self.metadata,self.expected)
    def verify(self,private=None):
        envelope,evidence=self.inspect();return r.verify_readback(envelope,private or self.private,self.expected,evidence)
    def test_inspect_is_not_private_custody_or_authority(self):
        with patch.object(r,'decrypt_result',side_effect=AssertionError('must not decrypt')):_,evidence=self.inspect()
        for field in ('private_readback_verified','durable_key_custody_verified','metadata_origin_independently_authenticated'):self.assertFalse(evidence[field])
        self.assertEqual(evidence['authorized_calls'],0)
        self.assertEqual(evidence['run_head_binding'],'MATCHED_SUPPLIED_GITHUB_METADATA_NOT_AEAD_FIELDS')
    def test_exact_receipt_verified_without_disclosure(self):
        evidence=self.verify();self.assertTrue(evidence['private_readback_verified']);self.assertFalse(evidence['durable_key_custody_verified'])
        self.assertNotIn('SYNTHETIC_PRIVATE',json.dumps(evidence));self.assertNotIn('PRIVATE KEY',json.dumps(evidence))
        self.assertEqual(evidence['receipt_sha256'],r.sha256(self.receipt))
    def test_wrong_key_and_ciphertext_tampering_fail(self):
        with self.assertRaisesRegex(r.ReadbackError,'AUTHENTICATION_FAILED'):self.verify(self.other)
        raw=bytearray(base64.b64decode(self.envelope['ciphertext_b64']));raw[-1]^=1
        self.envelope['ciphertext_b64']=base64.b64encode(raw).decode();self.archive=self.zip_bytes();self.rehash()
        with self.assertRaisesRegex(r.ReadbackError,'AUTHENTICATION_FAILED'):self.verify()
    def test_digest_failure_before_decrypt(self):
        self.archive+=b'changed'
        with patch.object(r,'decrypt_result',side_effect=AssertionError('must not decrypt')):
            with self.assertRaisesRegex(r.ReadbackError,'ARCHIVE_SHA256_MISMATCH'):self.verify()
    def test_every_expected_identity_is_checked(self):
        original=self.expected
        for field,value in dict(repository='other/repo',artifact_id=101,artifact_name='other',run_id=201,head_sha='f'*40,member_name='other.json',package_sha256='f'*64,recipient_sha256='f'*64,archive_sha256='f'*64).items():
            with self.subTest(field=field):
                self.expected=dict(original,**{field:value})
                with self.assertRaises(r.ReadbackError):self.inspect()
        self.expected=original
    def test_receipt_digest_required(self):
        self.expected['receipt_sha256']='f'*64
        with self.assertRaisesRegex(r.ReadbackError,'RECEIPT_SHA256_MISMATCH'):self.verify()
    def test_receipt_inner_package_required(self):
        self.receipt=b'{"package_sha256":"wrong"}';self.envelope=encrypt_result(self.receipt,self.public,'a'*64)
        self.expected['receipt_sha256']=r.sha256(self.receipt);self.archive=self.zip_bytes();self.rehash()
        with self.assertRaisesRegex(r.ReadbackError,'RECEIPT_PACKAGE_MISMATCH'):self.verify()
    def test_metadata_identity(self):
        original=copy.deepcopy(self.metadata)
        for field,value in [('id',True),('name','other'),('url','https://evil.invalid'),('archive_download_url',original['url']),('digest','sha256:'+'f'*64),('workflow_run',dict(id=True,head_sha='b'*40))]:
            with self.subTest(field=field):
                self.metadata=dict(original,**{field:value})
                with self.assertRaises(r.ReadbackError):self.inspect()
        self.metadata=original
    def test_expected_schema(self):
        for field,value in [('extra',True),('archive_sha256','A'*64),('run_id',True),('head_sha','main'),('member_name','../result.json'),('artifact_name','/absolute'),('repository','owner/repo/extra')]:
            with self.subTest(field=field),self.assertRaises(r.ReadbackError):r.validate_expectations(dict(self.expected,**{field:value}))
    def test_unsafe_zip_members(self):
        link=zipfile.ZipInfo('receipt.enc.json');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16;raw=json.dumps(self.envelope)
        for rows in [[('receipt.enc.json',raw),('extra','')],[('receipt.enc.json',raw),('receipt.enc.json',raw)],[('dir/','')],[('../receipt.enc.json',raw)],[('/receipt.enc.json',raw)],[(link,'elsewhere')]]:
            with self.subTest(rows=str(rows)[:60]):
                self.archive=self.zip_bytes(rows);self.rehash()
                with self.assertRaises(r.ReadbackError):self.inspect()
    def test_null_in_raw_zip_name_is_refused(self):
        self.archive=self.zip_bytes([('receipt.enc.jsonXhidden',json.dumps(self.envelope))]).replace(b'receipt.enc.jsonXhidden',b'receipt.enc.json\0hidden')
        self.rehash()
        with self.assertRaisesRegex(r.ReadbackError,'UNSAFE_OR_UNEXPECTED_ZIP_MEMBER'):self.inspect()
    def test_member_bound_before_expansion(self):
        with patch.object(r,'MAX_ENVELOPE',5),self.assertRaisesRegex(r.ReadbackError,'ENVELOPE_SIZE_LIMIT'):self.inspect()
    def test_archive_bound(self):
        with patch.object(r,'MAX_ARCHIVE',5),self.assertRaisesRegex(r.ReadbackError,'INPUT_SIZE_LIMIT'):self.inspect()
    def test_malformed_zip_and_json(self):
        for raw in [b'not JSON',b'{"schema":1,"schema":2}',b'NaN',b'[]']:
            with self.subTest(raw=raw):
                self.archive=self.zip_bytes([('receipt.enc.json',raw)]);self.rehash()
                with self.assertRaises(r.ReadbackError):self.inspect()
        self.archive=b'not a zip';self.rehash()
        with self.assertRaisesRegex(r.ReadbackError,'INVALID_ARTIFACT_ZIP'):self.inspect()
    def test_envelope_schema_and_encoding_bounds(self):
        original=self.envelope
        for field,value in [('extra',''),('schema','wrong'),('algorithm','wrong'),('nonce_b64','bad'),('nonce_b64',base64.b64encode(b'x').decode()),('wrapped_key_b64',''),('ciphertext_b64','')]:
            with self.subTest(field=field):
                self.envelope=dict(original,**{field:value});self.archive=self.zip_bytes();self.rehash()
                with self.assertRaises(r.ReadbackError):self.inspect()
        self.envelope=original
    def test_file_symlink_fifo_permissions_and_bounds(self):
        with tempfile.TemporaryDirectory()as root:
            path=Path(root)/'key.pem';path.write_bytes(b'not a private key');path.chmod(0o644)
            with self.assertRaisesRegex(r.ReadbackError,'OWNER_ONLY'):r.read_bounded(path,100,private=True)
            path.chmod(0o600);self.assertEqual(r.read_bounded(path,100,private=True),b'not a private key')
            actual=path.stat()
            with patch.object(r.os,'fstat',return_value=SimpleNamespace(st_mode=actual.st_mode,st_uid=os.geteuid()+1,st_nlink=1,st_size=actual.st_size)):
                with self.assertRaisesRegex(r.ReadbackError,'OWNER_ONLY'):r.read_bounded(path,100,private=True)
            hardlink=Path(root)/'hardlink';os.link(path,hardlink)
            with self.assertRaisesRegex(r.ReadbackError,'OWNER_ONLY'):r.read_bounded(path,100,private=True)
            hardlink.unlink()
            with self.assertRaisesRegex(r.ReadbackError,'INPUT_SIZE_LIMIT'):r.read_bounded(path,1)
            link=Path(root)/'link';link.symlink_to(path)
            with self.assertRaises(OSError):r.read_bounded(link,100)
            fifo=Path(root)/'fifo';os.mkfifo(fifo)
            with self.assertRaisesRegex(r.ReadbackError,'REGULAR_FILE_REQUIRED'):r.read_bounded(fifo,100)
    def test_cli_inspect_and_failures_are_sanitized(self):
        with tempfile.TemporaryDirectory()as root:
            root=Path(root);(root/'artifact.zip').write_bytes(self.archive);(root/'metadata.json').write_text(json.dumps(self.metadata));(root/'expected.json').write_text(json.dumps(self.expected))
            args=['inspect','--archive',str(root/'artifact.zip'),'--metadata',str(root/'metadata.json'),'--expected',str(root/'expected.json')]
            with contextlib.redirect_stdout(io.StringIO())as output:self.assertEqual(r.main(args),0)
            self.assertFalse(json.loads(output.getvalue())['private_readback_verified'])
            with contextlib.redirect_stdout(io.StringIO())as output:self.assertEqual(r.main(args+['--private-key','/SENSITIVE_PATH']),1)
            self.assertNotIn('SENSITIVE_PATH',output.getvalue())
            (root/'artifact.zip').write_bytes(b'changed')
            with contextlib.redirect_stdout(io.StringIO())as output:self.assertEqual(r.main(['verify']+args[1:]+['--private-key','/SENSITIVE_PATH']),1)
            self.assertEqual(json.loads(output.getvalue())['failure_code'],'ARCHIVE_SHA256_MISMATCH');self.assertNotIn('SENSITIVE_PATH',output.getvalue())
    def test_cli_verify_uses_only_in_memory_synthetic_key(self):
        files={'expectations':json.dumps(self.expected).encode(),'metadata':json.dumps(self.metadata).encode(),'archive':self.archive,'memory-key':self.private}
        def fake_read(path,maximum,*,private=False):self.assertEqual(private,path=='memory-key');return files[path]
        with patch.object(r,'read_bounded',side_effect=fake_read),contextlib.redirect_stdout(io.StringIO())as output:
            result=r.main(['verify','--archive','archive','--metadata','metadata','--expected','expectations','--private-key','memory-key'])
        self.assertEqual(result,0);self.assertTrue(json.loads(output.getvalue())['private_readback_verified'])
        self.assertNotIn('SYNTHETIC_PRIVATE',output.getvalue());self.assertNotIn('PRIVATE KEY',output.getvalue())
