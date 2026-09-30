import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import development_drc002_replay as replay
class DRC002HistoricalReplay(unittest.TestCase):
 def test_certified_package_runtime_and_git_blob_hashes(self):
  cert=replay.validate_archive()
  self.assertEqual(cert['package_sha256'],'fd4e55c4d50563374e5ba7c312a0268d027afa1533e4ecf165c0f976d5e9e081')
  self.assertEqual(cert['runtime_sha256'],'3734ddcd74524cc91f3fc32f3350b148c6e358d47585fb6827c0483c51cdb761')
 def test_archive_or_certificate_drift_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'corrupt.zip';path.write_bytes(replay.ARCHIVE.read_bytes()+b'drift')
   with patch.object(replay,'ARCHIVE',path):
    with self.assertRaisesRegex(ValueError,'archive drift'):replay.validate_archive()
   path=Path(tmp)/'corrupt.json';path.write_bytes(replay.CERT.read_bytes()+b' ')
   with patch.object(replay,'CERT',path):
    with self.assertRaisesRegex(ValueError,'certificate drift'):replay.validate_archive()
 def test_reopened_budget_cannot_be_used_in_replay(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'grant.json';path.write_text(json.dumps(dict(status='READY',remaining_usd=1,maximum_calls=1)))
   with patch.object(replay,'GRANT',path):
    with self.assertRaisesRegex(ValueError,'closed grant'):replay.replay()
 def test_closed_frozen_preflight_never_substitutes_runtime_or_rescores(self):
  result=replay.replay()
  self.assertEqual(result['provider_calls'],0);self.assertFalse(result['outputs_rescored'])
  self.assertFalse(result['latest_runtime_substituted'])
if __name__=='__main__':unittest.main()
