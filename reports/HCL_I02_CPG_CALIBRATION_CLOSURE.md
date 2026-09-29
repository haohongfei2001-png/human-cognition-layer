# I02 one-use C/P/G functional calibration — source-first closure

**Disposition: FAILED G-MAP SHAPE / PARTIAL C-P OBSERVATION / CLOSED_NO_RERUN.**
This is a functional qualification diagnostic on one already exposed MuSR
development source group. It is not a five-arm comparison, a scored independent
generalization result, or HCL efficacy evidence. H and H-new were excluded by
the failed native treatment-presence gate. The frozen package, prompts, source,
question and output contract were not changed after the run.

## 1. Source and question before model outputs

The author-team MuSR source describes Danny initially keeping the earphones in
the recording booth; Emma later moves them to the producer's desk. It also
says that when Danny moves Ricky's notebook to the desk, **"At the desk, he
glimpses a pair of earphones indirectly drawing his attention"**. The
question asks where Danny would *most likely look* for the earphones. Thus the
desk is supported by a later Danny-local observation, even though witnessing
Emma's move is not supported. A reported glimpse is not proof of a later
search or of Danny's private belief. The first group's second question was
excluded for unresolved perceptual support; no other source group or
confirmation answer was consulted for this run.

The source is the pinned author-team `TAUR-Lab/MuSR` CC BY 4.0 CSV, file
SHA256 `98cd17d2c9ea53664e274365e901c90dfcaa40d17547dfbd369f1cd26fd2a81c`;
first-group/source-text SHA256
`bd0aacf84d7bc7d7fd1fa4114dd05b17aa0c5f2c433d452dfd01b06f7b562d96`.
The dataset's label was never passed to an arm and is not treated as an oracle
for private knowledge or future behavior.

## 2. Frozen execution and immutable receipt

| Item | Recorded fact |
|---|---|
| Frozen package digest | `41d00a57678a75ccc867a34606bd3082c656e96dbd3ac1f47836338d7810f28c` |
| Trigger merge SHA | `a69e2e4ab516b04d0604a95ed1897689fb143fbd` |
| GitHub Actions run | [36561878435](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36561878435), attempt 1 |
| Artifact | `11029723107`, ZIP SHA256 `97628ea3e34235638173acf14ce50a6240bc36e7a237b249d5adde59659179f1` |
| [Full raw receipt](HCL_I02_CPG_CALIBRATION_RUN_36561878435/raw_receipt.json) | SHA256 `03ec86e3ce35df115d2acb892402ec8f33f3c4ffd62e13f563f3fda7e6aa02ce` |
| [Provider-free preflight](HCL_I02_CPG_CALIBRATION_RUN_36561878435/preflight.json) | SHA256 `4eaa11262d5945becb646841fbe44528b338dda39f9a7ffb1700d0c828de7eaa`; passed package, source, full ordinary input and USD 0.11841456 all-phase reservation below USD 0.12 cap |
| Actual model/configuration | All three responses report `deepseek-v4-pro`; thinking disabled, temperature 0, provider default service tier, no retries |
| Calls and usage | C: 1289 input + 185 output; P: 1391 + 188; G-map: 1323 + 151; 3 calls total, 0 retries, 0 G-final, 0 H/H-new |
| Cost | Usage-based estimated actual USD 0.00367950; rated peak USD 0.00735900; actual invoice cost unavailable. Hard cap USD 0.12; remaining authorization **zero**. No historical budget transfer. |

The raw receipt includes every issued request, raw response, actual model ID,
usage and phase-local parsed result, including the unsuccessful G-map response.
The workflow's normal exact-main checks passed; the one-shot workflow failed
at the G-map contract check after preserving the receipt.

## 3. Source-first interpretation of each response

- **C:** answered `producer's desk`. Its exact citation for Emma's movement is
  in the source, but its explanation assumes Danny knew of that movement and
  explicitly says the story does not confirm his knowledge. It misses the
  later explicit Danny-local glimpse. The location is source-plausible; the
  stated knowledge route is unsupported.
- **P:** answered `recording booth` and cited Danny's earlier placement there.
  It correctly separates Danny from Emma's unobserved move, but says Danny
  did not know the desk location despite the later quoted glimpse. This is a
  time/access reasoning error on the full source, not a missing-input error.
- **G-map:** returned an answer-shaped JSON object with `answer`,
  `source_citations`, `uncertainty`, `assumptions`, rather than the required
  `source_index` and `open_questions`. It cited the earlier booth placement
  and also omitted the later glimpse. The frozen runner rejected the shape
  before G-final; there is **no qualified G answer** and no H-over-G score.

No numeric semantic scorer or private-belief truth label was frozen for this
single functional calibration. These observations are a manual source-first
interface and reasoning audit, not accuracy points or statistical evidence.

## 4. Closure and next dependency-safe work

The one-use trigger is consumed. `run_attempt=1`, `budget_state=CLOSED_NO_TRANSFER_NO_RERUN`,
zero remaining budget and no repeat call apply even though only three of four
maximum calls occurred. A new provider-backed run would require a new,
separately frozen purpose and budget under current policy; it cannot silently
reuse this source or grant. The original frozen package and historical raw
receipt remain immutable.

**CAPABILITY_DELTA:** none from this calibration. The earlier ordinary
information-state entry repair remains provider-free correctness evidence.
The next implementation slice must improve general source-bound named
observation in ordinary narrative phrasing and repair the generic map interface
with provider-free checks. Independent source diversity, fair comparator
qualification and native H treatment presence remain open I02 requirements;
I03 paid efficacy comparison remains closed until they pass. LongMemEval was
SEALED / NOT ACCESSED. Leaderboard remains OFF.
