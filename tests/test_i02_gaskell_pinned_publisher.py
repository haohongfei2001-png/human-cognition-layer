"""Historical publisher transport may be cached, never rewritten or silently fetched."""
import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import i02_replay_gaskell_freeze as replay
class GaskellPublisherCacheTests(unittest.TestCase):
    def test_exact_raw_and_metadata_match_original_consumed_run(self):
        raw,rdf=replay.pinned_publisher_material()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'8fdafc01407ce9a54fa5b68135009d41f1eac1cdf71819b7bae03184d46a11eb')
        self.assertEqual(hashlib.sha256(rdf).hexdigest(),'bcbcb15658f9cfbc9ec71dac3cfdf8e445d3b8d63bc88cfae2ed3c1e6ebc21c3')
    def test_archive_tamper_fails_before_replay(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.zip';p.write_bytes(replay.PUBLISHER_CACHE.read_bytes()+b'x')
            with patch.object(replay,'PUBLISHER_CACHE',p):
                with self.assertRaisesRegex(ValueError,'archive drift'):replay.pinned_publisher_material()
if __name__=='__main__':unittest.main()
