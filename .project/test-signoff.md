# Test Sign-off Log

<!-- Immutable record. Append only — do not edit existing entries. -->

---

## P1 Incident — "Not Found" on POST /plan (2026-04-18)

**Date**: 2026-04-18
**Environment**: dev
**Severity**: P1 — primary chat feature non-functional for all dev users
**Status**: Resolved

### Root Cause
`mobile/.env` had `EXPO_PUBLIC_API_BASE_URL` without the `/dev` stage suffix since initial commit (2026-04-08). Every `POST /plan` hit `…amazonaws.com/v1/chat/plan` instead of `…amazonaws.com/dev/v1/chat/plan`. API Gateway returned its own bare `"Not Found"` string — Lambda was never invoked.

### Fixes Applied
| Fix | PR | Owner | Status |
|-----|-----|-------|--------|
| Append `/dev` to `EXPO_PUBLIC_API_BASE_URL` in `mobile/.env` | Direct edit | PM | Done |
| Write `EXPO_PUBLIC_API_BASE_URL` from Terraform outputs post-deploy in CI | PR #17 | DevOps | Merged |
| Add `$default` catch-all route to API Gateway (structured JSON 404) | PR #17 | DevOps | Merged |
| Add POST /v1/chat/plan smoke test to deploy-dev.yml | PR #18 | QA | Pending merge |

### Open Items
- POST /v1/chat/plan smoke test is non-blocking until a CI Cognito service account is provisioned (auth is required; no unauthenticated path exists in dev)
- Monitor Lambda invocation count for unexpected probe traffic via `$default` catch-all (24–48h post-deploy)

---

## Historical Test Results

### PR #15 — Thinking-Tag Stripping Fix (fix/strip-thinking-tags)

**Date**: 2026-04-18
**Branch**: `fix/strip-thinking-tags`
**Validated by**: QA Engineer

#### Summary

The thinking-tag stripping fix was validated against the unit test suite.

**Root cause**: Amazon Nova Pro emits `<thinking>` blocks inline inside the text content block of Bedrock Converse responses, rather than in a separate native reasoning block. These tags were reaching `PlanResult.message` and surfacing in the mobile chat UI.

**Fix**: After extracting the text content block in `orchestrator.py`, two `re.sub` calls strip the tags before `PlanResult` is constructed:

1. `re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()` — removes all `<thinking>` reasoning blocks.
2. `re.sub(r"<answer>(.*?)</answer>", r"\1", text, flags=re.DOTALL).strip()` — unwraps `<answer>` wrapper tags.

#### Tests

3 unit tests were added to `OrchestratorThinkingTagStrippingTests` in `backend/tests/test_orchestrator.py`:

| Test | Covers |
|------|--------|
| `test_thinking_tags_are_stripped` | Single `<thinking>` block removed; clean text returned |
| `test_answer_wrapper_tags_are_stripped` | `<answer>` wrapper unwrapped; inner content returned |
| `test_thinking_and_answer_tags_stripped_together` | Both tag types present in one response; both stripped |

All 3 tests passed.

#### Code reviewer warning (open item)

The code reviewer on PR #15 flagged that the `re.DOTALL` pattern `.*?` (non-greedy) combined with global substitution should handle multiple `<thinking>` blocks, but there was no explicit test for the multi-block case. This was logged as a warning finding and was addressed in the follow-on coverage work (see entry below).

---

### chore/coverage-to-80 — Multi-block `<thinking>` Regression Test

**Date**: 2026-04-18
**Branch**: `fix/strip-thinking-tags` (regression test added to close the PR #15 warning finding)
**Validated by**: QA Engineer

#### Summary

Added a fourth test, `test_multiple_thinking_blocks_all_stripped`, to `OrchestratorThinkingTagStrippingTests` to close the open warning finding from the PR #15 code review.

**Behaviour verified**: When Nova Pro emits multiple `<thinking>` blocks in a single text content block (e.g. `"<thinking>step 1</thinking>\n\n<thinking>step 2</thinking>\n\nFinal answer."`), the result is `"Final answer."` — all blocks stripped, no tag remnants in `result.message`.

**Rationale**: `re.sub` replaces all non-overlapping matches globally by default; this test confirms that property holds at the integration boundary (through `orch.plan()`) and not just as an assumption about the regex engine.

#### Tests run

| Class | Tests | Result |
|-------|-------|--------|
| `OrchestratorThinkingTagStrippingTests` | 4 | 4 passed |

Full class output:

```
tests/test_orchestrator.py::OrchestratorThinkingTagStrippingTests::test_answer_wrapper_tags_are_stripped PASSED
tests/test_orchestrator.py::OrchestratorThinkingTagStrippingTests::test_multiple_thinking_blocks_all_stripped PASSED
tests/test_orchestrator.py::OrchestratorThinkingTagStrippingTests::test_thinking_and_answer_tags_stripped_together PASSED
tests/test_orchestrator.py::OrchestratorThinkingTagStrippingTests::test_thinking_tags_are_stripped PASSED

4 passed in 0.03s
```

**Sign-off decision**: PASS — regression finding from PR #15 code review is closed.
