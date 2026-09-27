import itertools,unittest
from hcl.narrative_order import Anchor,Before,NarrativeOrder
class NarrativeOrderTests(unittest.TestCase):
    text='departure, arrival, meeting. Departure precedes arrival; arrival precedes meeting.'
    def node(self,phrase):
        i=self.text.index(phrase);return Anchor(i,i+len(phrase),phrase)
    def test_transitive_proof_and_no_presentation_order_assumption(self):
        events={n:self.node(n) for n in ['meeting','arrival','departure']}
        edges=[Before('departure','arrival',self.node('Departure precedes arrival')),Before('arrival','meeting',self.node('arrival precedes meeting'))]
        g=NarrativeOrder('source:world',self.text,events,edges);r=g.compare('departure','meeting');self.assertEqual(r['relation'],'BEFORE');self.assertEqual(len(r['support']),2);self.assertEqual(g.compare('meeting','departure')['relation'],'AFTER')
        empty=NarrativeOrder('source:reader',self.text,events,[]);self.assertEqual(empty.compare('departure','arrival')['relation'],'UNRESOLVED');self.assertEqual(empty.compare('departure','departure')['relation'],'SAME_EVENT')
    def test_scope_and_detachment(self):
        events={n:self.node(n) for n in ['departure','arrival']};edges=[Before('departure','arrival',self.node('Departure precedes arrival'))]
        g=NarrativeOrder('A:reported',self.text,events,edges);h=NarrativeOrder('B:reported',self.text,events,[]);events.clear();edges.clear();self.assertEqual(g.compare('departure','arrival')['relation'],'BEFORE');self.assertEqual(h.compare('departure','arrival')['relation'],'UNRESOLVED');self.assertEqual(g.compare('departure','arrival')['scope'],'A:reported')
    def test_contradiction_is_not_arbitrary_total_order(self):
        ev={n:self.node(n) for n in ['departure','arrival','meeting']};edge=self.node('Departure precedes arrival');g=NarrativeOrder('source',self.text,ev,[Before('departure','arrival',edge),Before('arrival','departure',edge)])
        self.assertEqual(g.compare('arrival','meeting')['relation'],'CONFLICT');self.assertGreaterEqual(len(g.compare('arrival','meeting')['cycle']),3)
    def test_anchor_integrity_and_unknown_endpoints(self):
        with self.assertRaises(ValueError):NarrativeOrder('source',self.text,{'a':Anchor(0,3,'lie')},[])
        with self.assertRaises(ValueError):Anchor(True,2,'xx').validate(self.text)
        with self.assertRaises(ValueError):NarrativeOrder('source',self.text,{'a':self.node('arrival')},[Before('a','b',self.node('arrival'))])
    def test_all_three_event_graphs_against_independent_linear_extensions(self):
        nodes=('a','b','c');poss=[(a,b) for a in nodes for b in nodes if a!=b];span=Anchor(0,1,'x');events={a:span for a in nodes}
        for bits in range(64):
            edges=[e for i,e in enumerate(poss) if bits&(1<<i)];orders=[p for p in itertools.permutations(nodes) if all(p.index(a)<p.index(b) for a,b in edges)];g=NarrativeOrder('fixture','x',events,[Before(a,b,span) for a,b in edges])
            for a,b in poss:
                expected='CONFLICT' if not orders else 'BEFORE' if all(p.index(a)<p.index(b) for p in orders) else 'AFTER' if all(p.index(a)>p.index(b) for p in orders) else 'UNRESOLVED'
                self.assertEqual(g.compare(a,b)['relation'],expected,(edges,a,b))
