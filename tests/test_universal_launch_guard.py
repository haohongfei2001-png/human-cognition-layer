import unittest
from scripts.universal_launch_guard import verify_run_history,verify_marker,MARKER,AUTHORIZATION

class LaunchGuardTests(unittest.TestCase):
    def row(self,id,event,second):return dict(id=id,event=event,created_at=f'2026-10-02T14:30:{second:02d}Z')
    def test_manual_and_push_share_one_first_run(self):
        for first,second in [('workflow_dispatch','push'),('push','workflow_dispatch')]:
            runs=[self.row(20,second,2),self.row(10,first,1)]
            self.assertTrue(verify_run_history(10,1,runs))
            with self.assertRaises(ValueError):verify_run_history(20,1,runs)
            with self.assertRaises(ValueError):verify_run_history(10,2,runs)
    def test_same_timestamp_has_one_deterministic_winner(self):
        runs=[self.row(11,'push',1),self.row(10,'workflow_dispatch',1)]
        self.assertTrue(verify_run_history(10,1,runs))
        with self.assertRaises(ValueError):verify_run_history(11,1,runs)
    def test_history_missing_current_or_fields_fails_closed(self):
        for rows in [[],[dict(id=1,event='push')],[self.row(1,'push',1)]]:
            with self.assertRaises(ValueError):verify_run_history(2,1,rows)
    def test_marker_binds_exact_package_grant_parent_and_only_changed_path(self):
        parent='a'*40;package='b'*64;grant='c'*64
        marker=dict(schema='hcl-universal-single-launch-marker-v1',authorization_ref=AUTHORIZATION,
            package_sha256=package,grant_sha256=grant,executor_commit=parent)
        self.assertTrue(verify_marker(marker,package,grant,parent,[str(MARKER)]))
        for bad in [dict(marker,package_sha256='d'*64),dict(marker,grant_sha256='d'*64),dict(marker,executor_commit='e'*40),dict(marker,extra=True)]:
            with self.assertRaises(ValueError):verify_marker(bad,package,grant,parent,[str(MARKER)])
        for paths in [[],[str(MARKER),'hcl/cognition/universal_entry.py'],['other.json']]:
            with self.assertRaises(ValueError):verify_marker(marker,package,grant,parent,paths)
