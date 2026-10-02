"""Pin bounded G04 integration and preserve every historical amendment unchanged."""
import hashlib
import json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_DEVELOPMENT_UNIVERSAL_ARGUMENT_AMENDMENT.json')
# Earlier live-tree restoration predates argument_analysis.py evolution. Pin
# every retained amendment script/report byte-for-byte, verify all consumed
# archives through the v24 chain, and reconstruct the exact prior G03 runtime
# by restoring ONLY the three explicitly amended runtime file hashes.
HISTORICAL_PINS = {
    'reports/HCL_DEVELOPMENT_ANSWER_BOUNDARY_AMENDMENT.json': 'ed044f76c7d2b296edbbd68bbff12f924883858a6708bd550490540f4f7dbfdf',
    'reports/HCL_DEVELOPMENT_COMPLETION_METADATA_AMENDMENT.json': 'd3ede4a8d3efe3bdf0b9a62f7fdb507448574a708ff722afdfa0e5c81cea02cc',
    'reports/HCL_DEVELOPMENT_EMBEDDED_SCENE_AMENDMENT.json': '6ae2202f34ed105b821e84d1e942cbba9642864c183b9fdb9bac20208e5b128e',
    'reports/HCL_DEVELOPMENT_METERED_UNIVERSAL_AMENDMENT.json': 'dfbe6dec18199a437a87c69e03e9562ebc39acda3a6252a27d1999497c263792',
    'reports/HCL_DEVELOPMENT_NARRATOR_ACTUAL_AMENDMENT.json': '3cba3300953341a71fe23b518ac169f481386837a9b5b0c7ce65af9bc455a06f',
    'reports/HCL_DEVELOPMENT_QUALIFIED_SPEECH_AMENDMENT.json': '56ee187b743c3d8a8b2b7ad632457e5a711d6c380c2c70bc9e2ebdc663308aac',
    'reports/HCL_DEVELOPMENT_READER_FINAL_BUDGET_AMENDMENT.json': 'ab1037d2fd4b443f31ca027fe13c1f051bdad8d41a5e7e30ed9338d9ba586d88',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V13.json': 'd92534614a46c3e9e709c8343e1bdb7ec8dbfddcada1872a25e638363885ffd9',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V14.json': '4a8d344496153e8c9a5dfd3a2daf82fe80703cc8d3718c5625c5f89a1e0cc781',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V15.json': '1329be3495422d64344019df7d857231c5a88199c7a09565f173783f00821b85',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V16.json': '52bbb28095ddc4058576e2a3230e0d71d4899dbb4b9cab144d61872ce88a31ea',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V17.json': '95163651c2842e50915b0131049654c453ea9ef5510347cb63944cdc3241bc50',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V18.json': '6ca26f9e706803923f51b16997fdcb20bc8eb3ffe1ca55b921f4b1d345384bcb',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V19.json': '5e63f055cb132b667f4eddad4e9d0f00b34524817e82b4e07ee1befc09943ce2',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V20.json': '8db451038219955b53d0376a04e6dfa9852e8fdd5f97cd36e3df51dbc8ca67f9',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V21.json': '856a3df3ac361004c525d6944daf753400d7e388519b068f276dfaeaff0fdbec',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V22.json': 'aa48eeb42d78ce68f6441ed061ccd56ddae5f5029df49394148cab8ab3887b70',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V23.json': '0e0d55680506dbae0f7b37b28f285c372a2a57b537789ac6ec9530211edae4da',
    'reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V24.json': 'cb4aa729835408a0826d99563f537a9eaf2670600e5b049f597a1ad9cf4b6ab2',
    'reports/HCL_DEVELOPMENT_SAFE_FAILURE_AMENDMENT.json': '937147296c6f54caee65dd4b23d677112a300d98413ec4357394cdcfe55968c3',
    'reports/HCL_DEVELOPMENT_UNIVERSAL_CONCEPT_AMENDMENT.json': '5d59641424fefdaa869c7636b609361cdc2b94199626fcbda040f47065387454',
    'reports/HCL_DEVELOPMENT_UNIVERSAL_NORMATIVE_AMENDMENT.json': '4de6782122d2b35f55fa0411c5d873583e352445e2f1c7e0807715261076545e',
    'reports/HCL_DEVELOPMENT_UNIVERSAL_QUESTION_AMENDMENT.json': '08bd9a87e5672fbb41f5120aa3846cc792ab6e59ce78287b1f763cb5da9ba152',
    'reports/HCL_I02_RUNTIME_AMENDMENT.json': 'c03aae79984556a20c2f5239329f059d80b439b003b3e444a5a847d2fb1bcefe',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V10.json': 'e483432ee1e28194934d7215ab3dc29e29d985009b87da6ea62819fef8c12409',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V11.json': '2e32feb199b14504b9f2c9a8841727a3bd427ea6cb1727a41a3f93dbed9643f8',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V12.json': '6af5d9ef259a916ef6d215deba359805e36190009aa5145db1e3fcaa0bb48337',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V2.json': '4afabbce214e40f1fe81747ce6843a87f98a45f47042f8be81a8f447b482aee2',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V3.json': 'f767e4e2c40c998108742f5df0877ac81e6a4350fba64cb5db392210ee28412c',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V4.json': 'e1bb08fe63cf4f52629a0aee17eaf692e0f59b943910b962ae6eb5cfa3b3c230',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V5.json': '22b2134e4daa7e80d3e5e258e33ee7438ff7afbac9b068060aad7bc75e59094b',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V6.json': '0262c058dee61a5a434bfff304bc3905d9a48f01ec8133b6ed7cd2884c718433',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V7.json': 'b7fbb8e348bd57207ebb55868c683b4bc17de0100159149b8ea9758bc82c0934',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V8.json': '66b87a04894a5e0127382aaf0432d06d3973525d4cafd5de09ff9fef629ca82f',
    'reports/HCL_I02_RUNTIME_AMENDMENT_V9.json': 'eefb3dea24b387cc52581f08c9064fa8c85b3a45b84784054d80968626a61ab8',
    'scripts/development_answer_boundary_amendment.py': '405981b6ed8a64064bf4534942e088119da8d1b16cb798097de8a94bcf5b50da',
    'scripts/development_completion_metadata_amendment.py': '9d789c1c620cb1e371664f4c76fced6066b8204c4ff530bdf0aaa243422aabf0',
    'scripts/development_embedded_scene_amendment.py': '550393384c24cfd408830accb113870366cbc247e3b2c208e17305c97165c6b2',
    'scripts/development_metered_universal_amendment.py': '889cdd717ef9bdf041728d4993387e48ac32bd7c4f0c097081889d78c517ba32',
    'scripts/development_narrator_actual_amendment.py': '772646429475b7f4eab0b3e47e7e454346e95d3f615ad97913d0d36119da033d',
    'scripts/development_qualified_speech_amendment.py': 'd6352e090250bfd55db4415c3636c649a41526008eb0c0393bd520830ed02eeb',
    'scripts/development_reader_final_budget_amendment.py': '24b8c621aba2f50e5509df44fee0ba8dc106db34f71ede3c1d758cbd72a170fe',
    'scripts/development_runtime_amendment_v13.py': '4ff42f13b55232cee6559f0a9787f13ac9a6188ec0df4b9c1c52756874a12a82',
    'scripts/development_runtime_amendment_v14.py': 'f953ae9cf26d31c081c2cb8d65a991de0c0d191d5ee6f2755e7a17f38bcac0ae',
    'scripts/development_runtime_amendment_v15.py': 'ac303a8fa792befcc90ac6ae30e1641dc37d6aefccec9ca8974ea6489b7c73b8',
    'scripts/development_runtime_amendment_v16.py': 'ab81e683eec877504694e50d3ad7bcd460f4d01770a211fddea698bcfac7c76b',
    'scripts/development_runtime_amendment_v17.py': '8fdb06ded96ac69316d0c000bad31944b08d03642dd3b921f99ded6d1cfe974a',
    'scripts/development_runtime_amendment_v18.py': '6b2c7d1b77483c97ea8d621c25e91dab2b32b3d4534f78395b968a3ca668dd1c',
    'scripts/development_runtime_amendment_v19.py': '29c8f0555f77134149d4f7c6c41d6d1e83b263c43cdbbf83ee552892897019cf',
    'scripts/development_runtime_amendment_v20.py': 'ce434958fccd65c81af83d390764a261c08bb6fafded25d99f089398f8ebe2fa',
    'scripts/development_runtime_amendment_v21.py': '945f14ff632f8dfda9ba9507fed9e1def3e7ab7cfc2ef2009c3a87b51ec958ec',
    'scripts/development_runtime_amendment_v22.py': '34f9b38fa668b73c42b1e5ee36d50e448d15e54a78323fc9fed004bd589f4137',
    'scripts/development_runtime_amendment_v23.py': '2d7fe563aea8ef2cde57ca754ffc99798b1baa152ce6f280a20c314c972f708d',
    'scripts/development_runtime_amendment_v24.py': 'f2b3c5811f3b87f89938bf8ccbe0d476d016bb3fc4dc8f23ae526d30b36167f8',
    'scripts/development_safe_failure_amendment.py': 'f1c5382051616f3def2a70389a8f6f64a3551cf47978fb15e1b0164ea2bf8454',
    'scripts/development_universal_concept_amendment.py': 'b4a300806b8e91f9c11e99605e6467623b30ec3161c92aa2521b9e7d679274f9',
    'scripts/development_universal_normative_amendment.py': '8130b19d3726a391fcb1851e755064d2e2cd31893116749ca5b3536bf44f9bdd',
    'scripts/development_universal_question_amendment.py': '971df7bbb78ded8c216da48fc04ecb105b6b8c292f6fcbdaf3f0bfadc92f0111',
    'scripts/i02_runtime_amendment_v10.py': '808f419ddec996db68b6ad319c28d269f842f6b41b4faf1d746b00de5c8c2b46',
    'scripts/i02_runtime_amendment_v11.py': 'e282064823c40bea4685dabc6bdd3892757733c61c501078319d30baa6799c48',
    'scripts/i02_runtime_amendment_v12.py': '950e4e7d511feb75855d64e07db2ccc1ff3c089cd0e093403ed4d404c7eedbc0',
    'scripts/i02_runtime_amendment_v3.py': 'c4954233f8c6b2b6ee49910b4f8213a91071ed96348c114d795ff53c9da2ba63',
    'scripts/i02_runtime_amendment_v4.py': '6d488a20c730d424aa125a0dc4bfb1df02125985b98c1ac5611d9b6dad5f132a',
    'scripts/i02_runtime_amendment_v5.py': '660fefbc01bcc01e86a9ffb8c7fb140859e6de06800bf3e56e30a1528b487937',
    'scripts/i02_runtime_amendment_v6.py': '7acbcd5be7aebe622e0cd1207cbe96f17605f0675157ed8c070077143fc7d3da',
    'scripts/i02_runtime_amendment_v7.py': 'ef8587cef93c2c6f4096ce8a7a1b8a2d3aa3fb408d23437ab2f601c213641fec',
    'scripts/i02_runtime_amendment_v8.py': '5bfb7f4d23f1f0d21abd7e179c4e63735ef1288e8b005275727419ca59fa3e05',
    'scripts/i02_runtime_amendment_v9.py': '5df66301b339d82b4e9486579cff21a4e8c3a90375c0047ef290bbd924a32fee',
}
PREVIOUS_FILES = {
    'hcl/cognition/argument_analysis.py': '897a34bea1952a49ae590a22bf06a8bff085921d0f9e2d2b11a42acc0a203752',
    'hcl/cognition/capability_catalog.py': 'c9bdf316bc555af4d8336188b16ae5b7f87cdf540e904083d45deb0ad408d425',
    'hcl/cognition/universal_entry.py': 'fa25bdcdfd640fb03f6dc940dee6616cc5deb040028cef18ac1b65a8661df90b',
}
PREVIOUS_RUNTIME = '026c918ef8937b1a6ea287b49a9b566c0f2df5cf5905d035cf729a6a365aac52'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment script or report changed')
    archive=validate_archive()
    validate_v24(current_digest=archive['runtime_sha256'])
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    restored=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if restored!=PREVIOUS_RUNTIME:raise ValueError('unrelated runtime or membership changed')
    expected={'schema': 'hcl-development-universal-argument-amendment-v1', 'previous_hcl_runtime_sha256': '026c918ef8937b1a6ea287b49a9b566c0f2df5cf5905d035cf729a6a365aac52', 'amended_hcl_runtime_sha256': 'eb1d5fad80254bf7e546e41595509713dc4167bf4c7004556d076bf0bbaf7e09', 'changed_runtime_files': ['hcl/cognition/argument_analysis.py', 'hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'G04_SINGLE_SOURCE_ARGUMENT_ADAPTER_AND_EXPLICIT_NEGATION_GUARD', 'provider_calls_in_preparation': 0, 'provider_spend_usd': 0, 'complete_capability_integration': False, 'model_planner_efficacy_verified': False, 'argument_grammar_extended': False, 'verdict_added': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('universal argument amendment drift')
    return True


if __name__=='__main__':validate_current();print('UNIVERSAL_ARGUMENT_CURRENT_RUNTIME_AND_HISTORICAL_CHAIN_PASS')
