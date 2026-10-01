"""Frozen development runtime/input replay; never paid execution or rescoring."""
import json,unittest
from pathlib import Path
from unittest.mock import patch
import scripts.development_drc005_replay as m
class ReplayTests(unittest.TestCase):
 def test_exact_archive_package_runtime_and_no_sealed_material(self):
  c=m.validate_archive();self.assertEqual(c['run_sha'],m.RUN_SHA);self.assertEqual(c['replay_allowed'],'PROVIDER_FREE_ONLY_NEVER_EXECUTE');self.assertTrue(all('longmemeval' not in n.casefold() for n in c['files']))
 def test_closed_grant_no_live_trigger_exact_inputs_only(self):
  r=m.replay();self.assertEqual(r['provider_calls'],0);self.assertFalse(r['latest_runtime_substituted']);self.assertFalse(r['outputs_rescored'])
 def test_live_grant_cannot_replay_or_spend_historical_remainder(self):
  original=Path.read_text
  def read(p,*args,**kw):return json.dumps(dict(status='READY',remaining_usd=1,maximum_calls=1)) if str(p)==str(m.GRANT) else original(p,*args,**kw)
  with patch.object(Path,'read_text',read):
   with self.assertRaises(ValueError):m.replay()
 def test_certificate_drift_refused(self):
  original=Path.read_bytes
  def read(p,*args,**kw):return original(p,*args,**kw)+b' ' if str(p)==str(m.CERT) else original(p,*args,**kw)
  with patch.object(Path,'read_bytes',read):
   with self.assertRaises(ValueError):m.validate_archive()
if __name__=='__main__':unittest.main()
