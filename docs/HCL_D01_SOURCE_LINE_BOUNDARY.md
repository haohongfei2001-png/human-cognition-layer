# D01 ordinary-entry line-separator boundary

The ordinary D01 adapter now admits only LF and CRLF source separators. Bare CR,
VT, FF, U+001C, U+001D, U+001E, U+0085, U+2028 and U+2029 return
D01_REQUIRES_LF_OR_CRLF_SOURCE with executed=false before native preparation.
The original source bytes and original outer question remain in the final input.
This restriction applies only to the source selected for D01.

## Reproduced false receipt

The native promise preparer derives source-line numbers by counting LF. Its B02
communication view recognizes Python splitlines separators. When those disagree,
a lookup can select an unrelated earlier actor's own expression as the promise.
For example, Noor's "Okay" followed by bare CR and Mira's conditional promise
produced OWN_EXPRESSION and conditions_received=true, despite no receipt cue.
LF and CRLF versions correctly produce EXPOSURE_UNKNOWN and false.

The retained-native recheck records the same false receipt for all nine rejected
separator forms, alongside the ordinary adapter's refusal. This repair does not
claim to fix the standalone retained native API. That format gap remains explicit;
B02's wider source-line representation is unchanged. No character, separator,
quote or offset is silently converted to make the source admissible.

## Bounded change and evidence

The runtime delta is three admission lines and one descriptor prefix. The check
recognizes CRLF on a temporary inspection string; it passes the original string
unchanged to the native preparer when admitted. It adds no parser, source facts,
actor mapping, provider calls or budget. Native promise lifecycle, receipt/history
semantics, B02 authority and all support/revision checks remain unchanged.

Four focused test methods cover every unsupported separator before native entry,
exact original-byte preservation, LF/CRLF controls with and without a real receipt,
unchanged B02 wide-separator behavior and isolation from unselected outer sources.
The pre-repair run recorded nine failed admission assertions. The recheck separately
preserves the native false-positive evidence; current full validation is recorded
in HCL_D01_SOURCE_LINE_BOUNDARY_VALIDATION.json.

The amendment preserves 142 historical pins and proves that removing only the
three-line guard and descriptor prefix restores the prior runtime byte-for-byte.
Earlier D01 reports remain historical snapshots. There is no new adapter, native
parser repair, historical rescore, provider invocation or model-efficacy claim.
D02 work remains separate, and B04 complete-evidence transport remains unresolved.
