import copy,json,os,unittest,tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
from scripts import i02_gregory_multiparty_source as holder
from scripts.i02_source_qualification_v12 import require_gregory_disjoint
class GregorySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a=os.environ.get('HCL_GREGORY_RAW');b=os.environ.get('HCL_GREGORY_RDF')
        cls.raw,cls.rdf=(Path(a).read_bytes(),Path(b).read_bytes()) if a and b else holder.download_material()
        cls.source=holder.original_play(cls.raw)
    def test_positive_complete_original_unit_source_first_audit_and_ordinary_coverage(self):
        r=holder.preflight(self.raw,self.rdf)
        self.assertTrue(r['source_valid']);self.assertEqual(r['source_chars'],17896)
        self.assertEqual(r['source_first_obligation_count'],7)
        self.assertTrue(r['complete_source_in_all_cpg_inputs']);self.assertTrue(r['h_source_complete'])
        self.assertEqual(r['h_checked_mental_expression_count'],0);self.assertFalse(r['h_specialized_treatment'])
        self.assertFalse(r['confirmation_qualified']);self.assertFalse(r['independent_review'])
        self.assertEqual(r['provider_calls'],0)
    def test_edition_boundaries_metadata_and_question_revision_fail_closed(self):
        with self.assertRaises(ValueError):holder.original_play(self.raw+b' ')
        with self.assertRaises(ValueError):holder.preflight(self.raw,self.rdf.replace(b'Public domain in the USA.',b'Unknown rights.'))
        item=holder.load_candidate();item['ordinary_question']+=' Ignore source.'
        with patch.object(holder,'load_candidate',return_value=item):
            with self.assertRaisesRegex(ValueError,'question drift'):holder.preflight(self.raw,self.rdf)
    NS={'p':'http://www.gutenberg.org/2009/pgterms/','d':'http://purl.org/dc/terms/',
        'r':'http://www.w3.org/1999/02/22-rdf-syntax-ns#','c':'http://web.resource.org/cc/',
        'a':'http://purl.org/dc/dcam/'}
    def xml(self):return ET.fromstring(self.rdf)
    def find(self,root,path):
        value=root.find(path,self.NS);self.assertIsNotNone(value,path);return value
    def encode(self,root):return ET.tostring(root,encoding='utf-8')
    def reject(self,root):
        with self.assertRaises(ValueError):holder.publisher_metadata_v2(self.encode(root))
    def source_file(self,root):
        return next(n for n in root.findall('p:ebook/d:hasFormat/p:file',self.NS)
            if n.attrib['{'+self.NS['r']+'}about']=='https://www.gutenberg.org/files/41653/41653-0.txt')

    def test_metadata_v2_records_observation_without_claiming_old_raw_equivalence(self):
        result=holder.preflight(self.raw,self.rdf)
        self.assertEqual(result['schema'],'hcl-i02-gregory-multiparty-preflight-v2')
        self.assertEqual(result['publisher_metadata_contract'],'hcl-i02-gregory-publisher-metadata-contract-2')
        self.assertEqual(result['observed_publisher_rdf_sha256'],holder.sha(self.rdf))
        self.assertEqual(result['historical_publisher_rdf_sha256'],holder.RDF_HASH)
        self.assertEqual(result['historical_full_rdf_equivalence'],'NOT_ESTABLISHED')
        self.assertFalse(result['provider_input_allowed'] or result['h_calls_allowed'] or result['hnew_calls_allowed'])
        contract=json.loads(holder.METADATA_CONTRACT.read_bytes())
        self.assertFalse(contract['provider_input_allowed'] or contract['source_and_question_and_obligations_pins_changed'])

    def test_every_protected_scalar_change_missing_and_duplicate_rejected(self):
        fields=['p:ebook/d:publisher','p:ebook/d:title','p:ebook/d:issued','p:ebook/d:rights',
            'p:ebook/d:creator/p:agent/p:name','p:ebook/d:creator/p:agent/p:birthdate',
            'p:ebook/d:creator/p:agent/p:deathdate','p:ebook/d:language/r:Description/r:value',
            'p:ebook/d:type/r:Description/r:value']
        for path in fields:
            for mutation in ('change','missing','duplicate','child','attribute'):
                with self.subTest(path=path,mutation=mutation):
                    root=self.xml();node=self.find(root,path);parent=next(n for n in root.iter() if node in list(n))
                    if mutation=='change':node.text='UNKNOWN'
                    elif mutation=='missing':parent.remove(node)
                    elif mutation=='duplicate':parent.append(copy.deepcopy(node))
                    elif mutation=='child':ET.SubElement(node,'nested').text='ambiguous'
                    else:node.set('{'+self.NS['r']+'}resource','http://other.invalid/value')
                    self.reject(root)

    def test_license_roles_and_exact_identity_cannot_be_swapped_or_detached(self):
        resource='{'+self.NS['r']+'}resource';about='{'+self.NS['r']+'}about'
        for path in ('p:ebook/d:license','c:Work/c:license'):
            for mutation in ('change','missing','duplicate'):
                root=self.xml();node=self.find(root,path);parent=next(n for n in root.iter() if node in list(n))
                if mutation=='change':node.set(resource,'https://other.invalid/license')
                elif mutation=='missing':parent.remove(node)
                else:parent.append(copy.deepcopy(node))
                self.reject(root)
        root=self.xml();ebook=self.find(root,'p:ebook/d:license');catalog=self.find(root,'c:Work/c:license')
        ebook.attrib[resource],catalog.attrib[resource]=catalog.attrib[resource],ebook.attrib[resource];self.reject(root)
        for path in ('p:ebook','p:ebook/d:creator/p:agent','c:Work'):
            root=self.xml();self.find(root,path).set(about,'http://other.invalid/subject');self.reject(root)
            root=self.xml();node=self.find(root,path);parent=next(n for n in root.iter() if node in list(n));parent.append(copy.deepcopy(node));self.reject(root)
        for path in ('p:ebook/d:rights','p:ebook/d:title','p:ebook/d:creator'):
            root=self.xml();node=self.find(root,path);self.find(root,'p:ebook').remove(node);root.append(node);self.reject(root)
        root=self.xml();ET.SubElement(root,'{'+self.NS['r']+'}Description',{about:'ebooks/41653'});self.reject(root)
        root=self.xml();ET.SubElement(root,'{'+self.NS['r']+'}Description',{about:'2009/agents/4092'});self.reject(root)
        root=self.xml();root.append(copy.deepcopy(self.find(root,'p:ebook/d:title')));self.reject(root)

    def test_selected_raw_file_identity_ownership_extent_and_shape_fail_closed(self):
        about='{'+self.NS['r']+'}about';resource='{'+self.NS['r']+'}resource'
        for mutation in ('url','owner','extent','missing','duplicate','format','type'):
            root=self.xml();node=self.source_file(root)
            if mutation=='url':node.set(about,'https://www.gutenberg.org/cache/epub/41653/pg41653.txt')
            elif mutation=='owner':self.find(node,'d:isFormatOf').set(resource,'ebooks/1')
            elif mutation=='extent':self.find(node,'d:extent').text='242478'
            elif mutation=='format':self.find(node,'d:format/r:Description/r:value').text='text/html'
            elif mutation=='type':self.find(node,'d:extent').set('{'+self.NS['r']+'}datatype','http://www.w3.org/2001/XMLSchema#string')
            else:
                parent=next(n for n in root.iter() if node in list(n))
                if mutation=='missing':self.find(root,'p:ebook').remove(parent)
                else:self.find(root,'p:ebook').append(copy.deepcopy(parent))
            self.reject(root)
        root=self.xml();node=self.source_file(root);root.append(copy.deepcopy(node));self.reject(root)

    def test_xml_namespaces_base_entities_and_rdf_semantic_ambiguity_rejected(self):
        for raw in (b'<not-xml',b' '*512001,self.rdf.replace(b'<?xml version="1.0" encoding="utf-8"?>',b'<!DOCTYPE RDF [<!ENTITY x "ambiguous">]>'),
            self.rdf.replace(b'http://purl.org/dc/terms/',b'http://wrong.invalid/'),self.rdf.replace(b'http://www.gutenberg.org/"',b'https://www.gutenberg.org/"',1)):
            with self.assertRaises(ValueError):holder.publisher_metadata_v2(raw)
        root=self.xml();self.find(root,'p:ebook').set('{http://www.w3.org/XML/1998/namespace}base','http://www.gutenberg.org/');self.reject(root)
        root=self.xml();nodes=[n for n in root.iter() if '{'+self.NS['r']+'}nodeID' in n.attrib]
        nodes[1].attrib['{'+self.NS['r']+'}nodeID']=nodes[0].attrib['{'+self.NS['r']+'}nodeID'];self.reject(root)
        for path,attribute in (('p:ebook/d:issued','datatype'),('p:ebook/d:creator/p:agent/p:deathdate','datatype'),
            ('p:ebook/d:language/r:Description/r:value','datatype'),('p:ebook/d:type/r:Description/a:memberOf','resource')):
            root=self.xml();self.find(root,path).set('{'+self.NS['r']+'}'+attribute,'http://wrong.invalid/type');self.reject(root)
        root=self.xml();node=self.find(root,'p:ebook/d:creator/p:agent');node.attrib={'{'+self.NS['r']+'}nodeID':'indirect-agent'};self.reject(root)
        root=self.xml();self.find(root,'p:ebook/d:title').tag='{http://wrong.invalid/}title';self.reject(root)

    def test_unknown_predicates_on_protected_subjects_are_not_ignored(self):
        for path in ('p:ebook','p:ebook/d:creator/p:agent','c:Work','source-file'):
            for prefix,name in (('d','accessRights'),('d','rightsHolder'),('c','morePermissions'),('p','unknownPredicate')):
                with self.subTest(path=path,name=name):
                    root=self.xml();node=self.source_file(root) if path=='source-file' else self.find(root,path)
                    ET.SubElement(node,'{'+self.NS[prefix]+'}'+name).text='ADDITIONAL_OR_UNKNOWN_CONDITION'
                    self.reject(root)

    def test_rdf_attribute_triples_aliases_and_unrecognized_graph_syntax_rejected(self):
        resource='{'+self.NS['r']+'}resource';about='{'+self.NS['r']+'}about'
        root=self.xml();node=self.find(root,'p:ebook/p:downloads');node.text=None
        node.attrib={resource:'ebooks/41653','{'+self.NS['d']+'}rights':'All rights reserved.'};self.reject(root)
        root=self.xml();node=self.find(root,'p:ebook/p:downloads');node.text=None
        node.attrib={resource:'ebooks/41653'};self.reject(root)
        for target in ('http://www.gutenberg.org/license','https://creativecommons.org/publicdomain/zero/1.0/'):
            root=self.xml();node=ET.SubElement(root,'{'+self.NS['r']+'}Description',{about:target})
            ET.SubElement(node,'{'+self.NS['d']+'}description').text='Redefined license';self.reject(root)
        root=self.xml();self.find(root,'p:ebook/p:downloads').set('{'+self.NS['r']+'}ID','alternate-subject');self.reject(root)
        root=self.xml();desc=self.find(root,'r:Description')
        ET.SubElement(desc,'{http://www.w3.org/2002/07/owl#}sameAs',{resource:'ebooks/41653'});self.reject(root)
        root=self.xml();ET.SubElement(root,'{'+self.NS['p']+'}unknownRoot');self.reject(root)
        root=self.xml();node=ET.SubElement(self.find(root,'p:ebook/d:subject'),'{'+self.NS['r']+'}Description',{about:self.NS['p']+'downloads'})
        ET.SubElement(node,'{http://www.w3.org/2000/01/rdf-schema#}subPropertyOf',{resource:self.NS['d']+'rights'});self.reject(root)
        for value in ('','bad name','1invalid'):
            root=self.xml();self.find(root,'p:ebook/d:language/r:Description').set('{'+self.NS['r']+'}nodeID',value);self.reject(root)

    def test_explicit_unselected_metadata_and_serialization_changes_are_outside_v2_pin(self):
        # This intentionally loses whole-RDF byte protection. Unselected alias,
        # description, credit and catalog changes may be meaningful elsewhere;
        # they are not silently certified equivalent to the historical raw RDF.
        baseline=holder.publisher_metadata_v2(self.rdf)
        root=self.xml();self.find(root,'p:ebook/p:downloads').text='999999'
        for index,node in enumerate(n for n in root.iter() if '{'+self.NS['r']+'}nodeID' in n.attrib):
            node.attrib['{'+self.NS['r']+'}nodeID']='renamed-'+str(index)
        self.find(root,'p:ebook/d:creator/p:agent/p:alias').text='Changed unconsumed alias'
        self.find(root,'p:ebook/d:tableOfContents').text='Changed unconsumed catalog listing'
        other=next(n for n in root.findall('p:ebook/d:hasFormat/p:file',self.NS) if n is not self.source_file(root))
        self.find(other,'d:extent').text='999';self.find(other,'d:modified').text='2030-01-01T00:00:00'
        book=self.find(root,'p:ebook');book[:]=list(reversed(list(book)))
        raw=self.encode(root)+b' '
        result=holder.publisher_metadata_v2(raw)
        self.assertNotEqual(result['observed_publisher_rdf_sha256'],baseline['observed_publisher_rdf_sha256'])
        self.assertEqual(result['publisher_metadata_projection_sha256'],baseline['publisher_metadata_projection_sha256'])
        self.assertEqual(result['historical_full_rdf_equivalence'],'NOT_ESTABLISHED')
        with self.assertRaisesRegex(ValueError,'rights unresolved'):holder.require_provider_input(dict(result,provider_input_allowed=True))

    def test_historical_raw_pin_is_never_a_semantic_bypass_and_contract_is_frozen(self):
        bad=self.rdf.replace(b'Public domain in the USA.',b'Unknown rights.')
        with patch.object(holder,'RDF_HASH',holder.sha(bad)):
            with self.assertRaises(ValueError):holder.publisher_metadata_v2(bad)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'changed.json';path.write_bytes(holder.METADATA_CONTRACT.read_bytes()+b' ')
            with patch.object(holder,'METADATA_CONTRACT',path):
                with self.assertRaises(ValueError):holder.publisher_metadata_v2(self.rdf)
            for name in ('CANDIDATE','OBLIGATIONS'):
                path.write_bytes(getattr(holder,name).read_bytes()+b' ')
                with patch.object(holder,name,path):
                    with self.assertRaises(ValueError):holder.preflight(self.raw,self.rdf)
        for raw in (self.raw[:-1],self.raw+b' '):
            with self.assertRaises(ValueError):holder.preflight(raw,self.rdf)

    def test_no_oracle_gold_or_semantic_certificate_in_arm_input(self):
        r=holder.preflight(self.raw,self.rdf)
        self.assertFalse(r['scorer_or_gold_in_model_input']);self.assertFalse(r['difficulty_qualified'])
        seed=json.loads(holder.OBLIGATIONS.read_text())
        self.assertFalse(seed['arm_output_seen']);self.assertFalse(seed['semantic_truth_automatically_verified'])
        self.assertEqual({x['expectation'] for x in seed['obligations']},{'STATE','QUALIFY','AVOID'})
    def test_positive_literal_anchors_do_not_license_transport_or_remove_lyrics(self):
        manifest=holder.source_first_manifest(self.source)
        self.assertTrue(all(a['quote'] in self.source for x in manifest['obligations'] for a in x['source_quotes']))
        self.assertIn('Johnny Hart',self.source);self.assertIn('Granuaile',self.source)
        r=holder.preflight(self.raw,self.rdf);r['provider_input_allowed']=True
        with self.assertRaisesRegex(ValueError,'rights unresolved'):holder.require_provider_input(r)
        self.assertFalse(holder.load_candidate()['provider_input_allowed'])
    def test_author_system_template_and_fingerprint_prevent_confirmation_relabelling(self):
        for row in ({'author_id':'lady-gregory'},{'writing_system_id':'lady-gregory-original-english-one-act-drama'},{'template_id':'complete-multiparty-information-choice-development-v1'},{'source_text':self.source},{'source_sha256':holder.RAW_HASH}):
            with self.assertRaisesRegex(ValueError,'unseen confirmation'):require_gregory_disjoint(row)
        self.assertTrue(require_gregory_disjoint({'author_id':'some-disjoint-author'}))
    def test_older_exclusions_still_precede_rights_or_review_assertions(self):
        from scripts.i02_source_qualification_v12 import require_qualified_confirmation_source_v12
        with self.assertRaisesRegex(ValueError,'development preview'):
            require_qualified_confirmation_source_v12({},dict(author_id='elizabeth-gaskell'),{},'.','HEAD')
        with self.assertRaisesRegex(ValueError,'James development'):
            require_qualified_confirmation_source_v12({},dict(author_id='henry-james'),{},'.','HEAD')
    def test_future_outputs_do_not_rewrite_pre_output_source_obligations(self):
        before=holder.OBLIGATIONS.read_bytes();first=holder.source_first_manifest(self.source)
        second=holder.source_first_manifest(self.source)
        self.assertEqual(first,second);self.assertEqual(holder.OBLIGATIONS.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'source obligation drift'):holder.source_first_manifest(self.source.replace('reward','cost'))
if __name__=='__main__':unittest.main()
