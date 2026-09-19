# HCL v0.3 Answer Checker Suite v0.2 — Fresh Adjudication

Run: `35415880531`

## Raw independent result

- fresh cases: **12**
- passed: **11 / 12**
- checker status accuracy: **91.7%**
- revision-family hit rate: **100%**
- final-check pass rate: **100%**
- schema/transport failures: **0**

The suite was created after the first checker run and therefore serves as fresh evidence.

## Sole raw failure — fresh12_second_order_explicit_bridge

Scene summary:
- Xiaoning sees Ajie leave.
- After Ajie leaves, Xiaoning sees the file moved from the desk into a cabinet.
- Xiaoning confirms Ajie did not return and did not receive a notification.

Question:
- What does Xiaoning think Ajie believes about the file location?

Candidate:
> 小宁会认为阿杰仍以为文件在桌上，因为她知道阿杰没有看到移动，也没有收到更新信息。

Fixture expected:
- PASS

### HCL state

The HCL state correctly detected an omitted bridge:
- the story never explicitly states that Ajie knew the file was on the desk **before leaving**;
- the story also never explicitly states that Xiaoning knows or assumes Ajie had that initial knowledge.

It therefore represented two live hypotheses and assigned medium uncertainty.

### Checker verdict

The checker returned:
- `REVISE`
- violation: `PREMATURE_COLLAPSE`

It revised the candidate into a conditional answer:

- if Xiaoning believes Ajie knew the original desk location, then she would think he still believes the file is on the desk;
- otherwise the story does not license a certain second-order belief.

The revised answer passed the final HCL check.

## Adjudication

**Fixture expectation error; checker behavior is correct.**

This is the same epistemic pattern identified by the research owner in the original CogToM seed audit:

> missing evidence about an agent's knowledge state must not be silently filled in merely because a conventional false-belief template would normally assume it.

The raw result remains **11 / 12**. It is not rewritten as 12 / 12.

## Checker gate decision

No checker-logic defect was found in the fresh suite.

Across the two checker suites:

### First suite
Run `35415496804`
- raw 9 / 12
- revision-family hit rate 100%
- final-check pass rate 100%
- all three raw failures were adjudicated as test-harness/fixture issues.

### Fresh suite
Run `35415880531`
- raw 11 / 12
- revision-family hit rate 100%
- final-check pass rate 100%
- sole raw failure was a fixture that omitted an initial-knowledge bridge.

Therefore:

**HCL v0.3 answer checker gate: PASSED**

Next:
1. integrate the always-on loop into task execution;
2. run a small CogToM regression diagnostic;
3. begin SOTOPIA-Hard integration with a custom agent class.
