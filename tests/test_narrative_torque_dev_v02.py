import json,unittest
from unittest.mock import patch
from scripts import run_narrative_torque_dev_v01 as old
from scripts import run_narrative_torque_dev_v02 as r
from tests import test_narrative_torque_dev_v01 as fixtures
# Reuse meaningful state/question/gold firewall, preservation, offset and no-fallback gates.
class RepairTests(fixtures.TorqueTests):
 def setUp(self):
  p=patch('tests.test_narrative_torque_dev_v01.r',r);p.start();self.addCleanup(p.stop)
 def test_json_mode_requirement_independent_of_source(self):
  i=self.item();self.assertNotIn('json',json.dumps(old.graph_messages(i)).lower());r.validate_request_shape([i])
  with patch.object(r,'GRAPH',old.GRAPH):
   with self.assertRaisesRegex(ValueError,'JSON mode'):r.preflight([i])
 def test_failure_retains_attempted_request_and_sanitized_diagnostic(self):
  class Bad(Exception):status_code=400
  class F:
   def complete_json(self,messages,**kwargs):raise Bad('json must be in messages; secret=NEVER_ARCHIVE')
  rows,fail=r.execute([self.item()],{'fixture':self.native()},{a:F() for a in r.CAPS})
  self.assertEqual(rows[0]['graph']['actual_messages'],r.graph_messages(self.item()));self.assertIsNone(rows[0]['graph']['raw_response']);self.assertEqual(fail[0]['diagnostic'],'JSON_MODE_PROMPT_REQUIREMENT');self.assertEqual(fail[0]['status_code'],400);self.assertNotIn('NEVER_ARCHIVE',json.dumps(fail))
 def test_repair_selection_is_v01_and_budget_is_separate(self):
  self.assertEqual(r.SALT,old.SALT);self.assertEqual(r.CAPS,old.CAPS);self.assertEqual(r.COMMON,old.COMMON);self.assertEqual(r.THIN,old.THIN);self.assertNotEqual(r.TOKEN,old.TOKEN)

 def test_partial_transport_preserves_first_arm_without_retry(self):
  calls=[];parent=self
  class F:
   def __init__(self,a):self.a=a
   def complete_json(self,m,**kw):
    graph=m[0]['content']==r.GRAPH;calls.append('graph' if graph else self.a)
    if graph:return parent.graph()
    if self.a=='P':raise RuntimeError('uncertain transport')
    return json.dumps({'events':[{'quote':'beta','occurrence':0}],'reason':'x'})
  rows,fail=r.execute([self.item()],{'fixture':self.native()},{a:F(a) for a in r.CAPS})
  self.assertEqual(calls,['graph','C','P']);self.assertTrue(fail);self.assertTrue(rows[0]['arms']['C']['agrees_with_native_reference']);self.assertEqual(rows[0]['arms']['P']['actual_messages'],r.messages(self.item(),'P'));self.assertIsNone(rows[0]['arms']['P']['raw_response']);self.assertNotIn('T',rows[0]['arms'])
