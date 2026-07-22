---
name: brainstorm
description: Start a behavior brainstorm session for a new feature — the mandatory first phase of BDK feature work. Produces an approved behavior spec before any implementation discussion.
argument-hint: <feature-slug or one-line requirement>
---

# BDK behavior brainstorm

You are running a **behavior brainstorm session**. Its only output is a behavior spec at
`.bdk/specs/<slug>.spec.md`. Implementation talk is out of bounds: while this session is
active, hooks block you from reading source code and from editing anything except the spec.
Repo context comes exclusively through the `bdk-recon` agent, which reports behavior, never
internals. If you or the user drift into internals ("we'll add a helper class that…"),
redirect: *"that's a GREEN/REFACTOR concern — what should the caller observe?"*

BDK scripts directory (call with `python3`): `${CLAUDE_SKILL_DIR}/../../scripts`

Feature argument: `$ARGUMENTS`

## Session protocol — fixed sequence, one step at a time

Run the steps in order. Use AskUserQuestion with concrete candidate answers at each
elicitation step. If the user answers "defaults", fill the step with your best proposal and
move on. Keep a running draft; render the full spec only at step 10.

**0. Preflight.** If `.bdk/config.json` doesn't exist, stop and tell the user to run
`/bdk:init` first. Otherwise derive a kebab-case slug from the argument and run:
`python3 <scripts>/bdk_state.py init <slug>` (this enters BRAINSTORM and arms the hooks).

**1. Intake.** Confirm the requirement as ONE sentence in user language. Classify size:
genuinely obvious one-liner → suggest `/bdk:gear 5` (skip-ahead); unknown territory →
mention low gear (throwaway exploratory tests, deleted at /bdk:done); otherwise gear 4.

**2. Recon.** Dispatch the `bdk-recon` agent with the requirement sentence. Validate its
report has exactly the five required sections and no internal identifiers; if internals
leaked, re-dispatch with a correction note. Present findings to the user as *"what the
system already does around this"* — existing behaviors in G/W/T form, the ports involved,
test conventions worth reusing, known invariants, and hazards (these feed step 9).

**3. Behavior enumeration.** Elicit behaviors as Given/When/Then with IDs (B1, B2…).
Happy paths first, then force the edge sweep — ask about each: empty/none? huge?
duplicates? weird unicode? concurrent? unauthorized? already-done (idempotence)?
boundary values? Behaviors must describe *observable outcomes at the port*, not mechanics.

**4. Non-goals.** Explicit out-of-scope list — this is the anti-gold-plating contract that
GREEN is held to.

**5. Contract surface.** Name the port/facade under test (an existing port from recon, or a
new one). Record inputs, outputs, error modes as signatures/types only, plus observable
events. Hard rule: internal collaborators, data structures, and algorithms are banned here.

**6. Property hunt.** Walk the eight catalog questions below with the user. Record
properties as P1, P2… tagged with their pattern. If none surface: that's a
requirement-clarity alarm (Wlaschin) — loop back to step 3 once; only after a second pass
may the user sign "No non-trivial property found — justification: …".

@references/property-catalog.md

**7. EDFH analysis.** Run the drill: describe the laziest implementation that passes the
example tests alone; add properties until that paper-cheat dies; record cheat + killer
P-IDs + accepted residual gaps in the spec.

@references/edfh-heuristic.md

**8. Test plan.** One example test per behavior (documentation role) + property tests per
property. Place each on the pyramid: port-level (default) / integration (adapter wiring
ONLY) / e2e (thin). Note the stack's PBT library from `.bdk/config.json` (`pbt` field).

**9. Mock policy.** Enumerate the port's dependencies (recon's hazards section helps).
Per dependency choose real / in-memory fake / mock — default **real**; the only two
acceptable justifications for a double are *expensive resource* and *shared-fixture
hazard*. Anything else gets the real thing.

**10. Assembly & approval.** Render the spec using the template below, write it to
`.bdk/specs/<slug>.spec.md`, and ask the user to approve. On approval: set Status:
APPROVED with today's date, run `python3 <scripts>/bdk_gate.py check-spec` (fix findings
if any), then `python3 <scripts>/bdk_state.py phase RED "spec approved"` and hand off to
`/bdk:red`.

@references/spec-template.md
