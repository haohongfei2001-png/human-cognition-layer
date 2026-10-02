"""Fresh fixed synthetic diagnostics, with no model invocation or historical replay."""
from decimal import Decimal

AUTH='OWNER_CONFIRMED_2026_10_02_I02_NEW_1_USD_12_CALLS'
RUNTIME_COMMIT='df0c5d3cdf60219ad0ceab8b25a7bf82ac8087be'
RUNTIME_SHA256='ad67e85c9bd00cb23dd61825bf7c35790f72282754574da19612435e96839cfe'
EXPIRES_AT='2026-10-03T08:00:00Z'
CAP=Decimal('1.00')
MAX_CALLS=12
MAX_REQUEST_BYTES=18000
MAX_WAIT_SECONDS=180
MAX_ELAPSED_SECONDS=1800
PROBE_QUESTION='Explain how trust and shared rules can influence cooperation in a small community. Distinguish a useful general model from evidence about any particular person.'
CASES=[
    dict(case_id='coordination_without_source',question='How can individual incentives and shared expectations affect coordination in a volunteer group? Explain limits of the general analysis.',sources={}),
    dict(case_id='competing_public_goals',question='What possible reasons for Rina leaving are supported by the reports, and is a unique actual motive established?',sources={'meeting':'\n'.join([
        'Rina said, "I want to finish the draft."',
        'Rina said, "I plan to leave the meeting in order to finish the draft."',
        'Rina said, "I want to avoid the noise."',
        'Rina said, "I plan to leave the meeting in order to avoid the noise."',
        'Rina said, "At the time, I knew about the meeting."',
        'Rina said, "At the time, I could leave the meeting."',
        'Rina said, "I left the meeting."'])}),
    dict(case_id='conditional_argument_change',question='If Tavi could decline were false, what changes?',sources={'choice':'Narrator: In choice, Tavi could decline.\nTavi: In choice, I conclude choice is voluntary because Tavi could decline.'}),
]
