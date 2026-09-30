"""Exclude the native-choice writing system used for a generic entry correction."""
from scripts.i02_source_qualification_v7 import require_qualified_confirmation_source_v7

SYSTEM='tombench-original-bilingual-social-scenarios'
AUTHORS=frozenset({'zhuang-chen-tombench-author-team','zhuang-chen','jincenzi-wu','jinfeng-zhou',
    'bosi-wen','guanqun-bi','gongyao-jiang','yaru-cao','mengting-hu','yunghwei-lai','zexuan-xiong','minlie-huang'})

def require_qualified_confirmation_source_v8(freeze,candidate,audit,repository,revision,lineage=None):
    if not isinstance(candidate,dict):
        raise ValueError('candidate must be an object')
    if (candidate.get('writing_system_id')==SYSTEM or candidate.get('author_id') in AUTHORS or
            candidate.get('template_id')=='tombench-native-four-option-v1'):
        raise ValueError('native-choice development entry system cannot be confirmation')
    return require_qualified_confirmation_source_v7(freeze,candidate,audit,repository,revision,lineage)
