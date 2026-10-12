---
name: mathematica
description: "Run Mathematica (wolframscript) for symbolic and high-precision work, decide when it beats Python, and write .nb notebooks programmatically. Use this skill whenever a task needs exact symbolic computation (series, closed-form integrals or ODE solutions, special functions, exact rational or polynomial algebra, Simplify-to-zero proofs), arbitrary-precision numerics with precision tracking, high-precision ODE integration, closed-form recognition of a numeric constant (PSLQ), or a Mathematica notebook as the deliverable. Triggers include: 'solve this symbolically', 'expand as a series', 'closed form', 'exact coefficient', 'derive rather than fit', 'high precision', '30 digits', 'identify this constant', 'DSolve', 'wolframscript', 'Mathematica', 'make a Mathematica notebook', '.nb file', or any moment a Python route would mean re-implementing computer algebra."
---

# Mathematica from Claude Code

Needs a Wolfram kernel and `wolframscript` on PATH, supplied by Mathematica or the
Wolfram Engine with its own licence. Check with `wolframscript -c '$Version'`.
If the command is not on PATH but Mathematica is installed, find it inside the
application bundle. On a Mac, it is at `Contents/MacOS/wolframscript` within the
Wolfram, Mathematica or WolframScript app. Use the full path or link it onto PATH.
If it is not installed, tell the user before using sympy or mpmath, and explain
what those cannot do. The process commands below (`pgrep`, `ps`) are for macOS
and Linux.

## When Mathematica is the right tool

- Use it for exact symbolic work: Series (including expansions with logarithmic
  terms), DSolve, Integrate in closed form, Solve/Reduce over polynomial systems,
  symbolic linear algebra and Limit. Python's sympy handles parts of this work
  but is far weaker on coupled ODEs, special functions and hard simplifications.
- Proofs by simplification: `Simplify[lhs - rhs] === 0` with assumptions.
  An exact zero is a verdict, not a fit.
- Arbitrary precision WITH precision tracking: numbers carry their own
  accuracy, so catastrophic cancellation is visible (Precision[x]; a
  printed 0``-120 means a zero known only to accuracy -120, which is a
  diagnosis, not noise). mpmath gives digits but not this bookkeeping.
- High-precision ODE integration: NDSolve at WorkingPrecision 30-50 is
  routine; nothing in the Python stack matches it.
- Constant recognition: FindIntegerNullVector (PSLQ), RootApproximant,
  Rationalize - the closing move after a 25-digit numeric result.
- Special functions done right: PolyLog, Hypergeometric2F1, LerchPhi at
  arbitrary precision and symbolic argument.

## When Python (or the shell) is the right tool

- Data wrangling, files, text, web plots, APIs, glue: Python.
- Bulk machine-precision numerics over arrays: numpy, by a wide margin.
- Anything leaning on an ecosystem (pandas, ML, requests): Python.
- Quick arithmetic: python3/bc are instant; wolframscript pays seconds
  of licence-check startup on every call.
- Massive parallelism: the licence caps subkernels (see Licence
  discipline), so a machine with more cores than the cap still
  parallelises only that many ways.

The dividing line: if the result's value depends on being EXACT (a
rational, a closed form, a proof of zero) or on digits beyond machine
precision being TRUSTWORTHY, use Mathematica. If it depends on
ecosystem, throughput, or plumbing, use Python.

## How to run the kernel

- One-liner, result auto-printed: `wolframscript -c '1/3 + 1/7'`
  (the value of the last expression is printed; use Print for
  intermediate output).
- Script file: `wolframscript -file script.wls`. Shebang
  `#!/usr/bin/env wolframscript` works for executables.
- Every call is a FRESH kernel: no state survives between calls.
  Persist intermediate results with `Put[expr, "file.m"]` and reload
  with `Get["file.m"]` - exact expressions round-trip losslessly,
  including arbitrary-precision numbers and symbols.
- Batch related work into one call. Startup takes a few seconds for the licence
  check, so many small calls repeat that cost.
- Read command-line arguments from `$ScriptCommandLine` (element 1 is the script
  path). Any script that reads arguments MUST include a usage example in its
  header comment. Without it, the invocation cannot be reconstructed later.
- Exit codes: `Exit[0]` success, nonzero for failure; gate results and
  exit accordingly so shell callers can branch.
- Long runs: launch detached with output redirected to a log file, poll
  the log, and note that kernel output is BUFFERED - a run can look
  silent for many minutes at full CPU, then flush at once. Judge
  liveness by `ps aux | grep WolframKernel` (CPU time advancing), not
  by the log.

## Licence discipline

A Wolfram licence caps the number of top-level kernel processes and of
subkernels, and the caps differ between licences. Read them from the
kernel rather than guessing:

    {$MaxLicenseProcesses, $MaxLicenseSubprocesses}

Typical limits are small, such as {2, 8}, and apply machine-wide to every Wolfram
process, whatever started it. The Mathematica front end, a wolframscript call
and an MCP server all use the same licence pool. Before launching anything:

    pgrep -fl WolframKernel

A limit of two processes sounds roomy and is not. The front end holds one
whenever Mathematica is open, leaving exactly one for everything else. If
a kernel is running (another session, project or application may own it),
wait or coordinate; once the limit is reached, the front end included, the
next wolframscript fails rather than queues.

**The subkernels are one pool, and the first master to ask takes it.**
While one master holds the whole pool, a second master's `LaunchKernels[]`
gets 0. The holder is also refused if it asks for more than the cap.
Each refusal prints `No valid password found`.

A master with
no subkernels does not fail: `ParallelTable`, `ParallelSubmit` and `WaitNext`
print a `nopar` warning ("No parallel kernels available; proceeding with sequential evaluation")
and run every job serially on the master, with correct results and exit 0.
A campaign without the pool takes as many times longer as the pool had kernels,
using its time budget without reporting a failure. A parallel script should
check as follows:

    n = Min[$MaxLicenseSubprocesses, $ProcessorCount];
    If[$KernelCount == 0, LaunchKernels[n]];
    If[$KernelCount < n, Print["only ", $KernelCount, " subkernels"]; Exit[1]];

Start the parallel master first. A second master can do serial work alongside
the parallel campaign and slows it only a little. For serial work, call no
Parallel function at all. Those functions launch kernels on first use and
would either take the pool or use sequential evaluation with `nopar`.

**A refused kernel lies about why.** It exits non-zero with `No valid password found`, or
wolframscript reports "not activated or experiencing a license-related problem". This message
means the licence pool is full, not that the licence is broken, and investigating the licence
file and configuration on that basis can take hours. Check `pgrep -fl WolframKernel` first,
every time.

If a refusal appears while slots seem free, account for every running kernel
first. Then try once from a normal terminal before drawing a conclusion.
Kill runs by PID and verify with pgrep afterwards. Pattern-kills leave the
kernel running unobserved for hours. Follow any stricter local rules in a
project's CLAUDE.md or AGENTS.md when working inside that repo.

## Reliability rules

- **Quiet@Check is a results-killer.** Two-argument `Check` returns its failure value on ANY
  message, including harmless warnings (FindRoot::precw, a jsing at a fold that then
  converges). `Quiet[Check[expr, fail]]` still returns `fail`, as the outer Quiet only
  suppresses printing. `Check[Quiet[expr], fail]`, or `Off` before Check, hides the message
  from Check, so it does not return the failure value. If checking messages, name them with
  `Check[expr, fail, {NDSolve::ndsz, NDSolve::mxst}]` or use `Off` for known-benign ones.
  Best of all, test the returned VALUE (numeric, finite, of a sane size) instead of relying
  on messages.
- **Cap risky symbolic calls.** DSolve, Integrate, FullSimplify can hang
  or die on RecursionLimit. Wrap them:
  `TimeConstrained[expr, 600, "TIMEOUT"]` and handle the sentinel, with
  the guard placed close to the risky call.
- **Comment trap in .wls files:** any `*)`-forming text inside a
  `(* ... *)` comment (a literal "A4*)" for instance) terminates the
  comment and the script dies at parse with a misleading error. Balance
  every bracket before a long run; a small checker that strips comments
  and strings and balances brackets saves hours.
- **Function renames its variable:** `Function[x, Evaluate[body]]`
  silently renames to x$ and derivatives evaluate to zero. Build with
  `Function @@ {var, body}` instead.
- **Branch garbage near special-function branch points:** Series of
  PolyLog/Log composites at symbolic points injects complex
  Floor[Arg[...]] artefacts. Rewrite first with inversion identities
  (Li2(v) = Pi^2/6 - Log[v] Log[1-v] - Li2(1-v) moves an argument near
  1 to one near 0) and expand with real assumptions.
- **NDSolve on implicit systems:** large coupled second-order systems
  fail with NDSolve::ntdv (cannot isolate derivatives) or grind forever
  in preprocessing. Pre-solve symbolically for the highest derivatives
  (the coefficient matrix is usually small and rational even when the
  sources are enormous) and hand NDSolve the explicit form.
- **Machine precision is poison in sensitive pipelines.** Where errors amplify (shooting
  methods, oscillatory solutions, near-cancellations), use `WorkingPrecision -> 25` or more
  and SetPrecision all inputs. Certify stability by rerunning at two precisions and comparing.
- **Real-branch hygiene after DSolve:** raw output often contains Log[1-s], ArcTanh and
  PolyLog[2, s^2] forms that are complex on the required real interval. Rewrite them to the
  real branch (Log[s-1], ArcTanh split into logs, the dilog inversion) before evaluating
  anything.
- **Never assign to a symbol that loaded code uses as a variable.**
  A top-level `r = Get[...]` in a quick diagnostic script silently breaks
  code that builds equations in global symbols (r, x, s). Later
  Series/D/NDSolve calls use the assigned value as their variable and fail
  with ivar/dsvar messages. They may also fail quickly with output that looks
  like a genuine result. Use fresh names (rr, res0) in quick scripts,
  with the same care as in the main ones.

## Verification: match the weight to the stakes

Most Mathematica use is everyday computation - solving an equation for
a course, an integral for a figure, an exploration. For that, verify
cheaply and move on:

- spot-check a symbolic result numerically at a random point
  (`Integrate` vs `NIntegrate`, a DSolve solution substituted back);
- check one limit or special case where the answer is known;
- and that is enough. Do not build gates around a course example.

Escalate to the proof patterns below only when the result is
LOAD-BEARING: it will be published or taught as fact, other results
build on it, it contradicts an expectation or an earlier result, it
was hard to reach (many failure modes on the way), or two methods
disagree. The cost of the machinery is real; spend it where being
wrong is expensive.

## Proof patterns for load-bearing results

- **Held-out equation with teeth.** Solve using a subset of the
  equations, keep one out entirely, and gate that it vanishes on the
  solution - an unfitted witness. Then corrupt one derived coefficient
  and confirm the held-out equation now fails, proving the check can
  detect error at all.
- **Control run with the old assumption.** When a changed assumption changes a result, rerun
  the same code with the old assumption restored. Require exact reproduction of the old result
  before accepting the new answer as a consequence of the stated change, not a bug.
- **Known results first.** Code that extends a calculation re-derives
  the results already established (lower orders, special cases) in the
  same script before computing anything new.
- **Two independent computations.** The strongest form: two computations
  sharing no code or data, matched term by term in exact rationals, with
  conventions fixed in the code rather than converted by hand.
- **Reading an unknown asymptotic form from data.** Sample the function and take successive
  differences (against Log[x] where logarithms may appear). Estimate the powers and
  logarithmic terms, add that form to the fit, and check that the residual falls to the noise
  level. The estimate proposes the form, and the refit confirms it.
- **Finding the inconsistent condition.** When a linear system of conditions has no solution,
  use per-row residuals and leave-one-out solves to identify the inconsistent condition instead
  of guessing.
- **Independence discipline.** Runs that inherit each other's starting
  guesses can never corroborate one another; certify by independent
  restarts and by re-substituting the claimed answer into the original
  equations. And test VALUES, not shape: a degraded solver return can
  be a well-formed rule list carrying garbage, so validity checks
  evaluate the returned functions and demand finite, sane numbers.

## Script skeleton (gated, exit-coded)

```mathematica
#!/usr/bin/env wolframscript
(* what this computes, one comment; never let a close-paren-star
   sequence appear inside it. usage: wolframscript -file this.wls *)
fails = 0;
gate[l_, ok_] := Which[ok === True, Print["PASS  ", l],
   ok === False, Print["FAIL  ", l]; fails++,
   True, Print["ABORT non-boolean: ", l]; Exit[2]];
expr = Sin[x]^2 + Cos[x]^2 - 1;  (* the expression to prove zero *)
result = TimeConstrained[FullSimplify[expr], 600, "TIMEOUT"];
gate["the identity holds", result === 0];
If[!DirectoryQ["results"], Quiet[CreateDirectory["results"]]];
gate["result saved", Quiet[Put[result, "results/this-run.m"]] =!= $Failed];
If[fails > 0, Exit[1], Print["ALL GATES PASS"]];
```

## Writing notebooks (.nb)

A .nb file is plain text holding a `Notebook[{Cell[...], ...}]`
expression, so a headless kernel can generate one with Export - no
front end needed:

```mathematica
nb = Notebook[{
   Cell["Closed form for the Basel sum", "Title"],
   Cell["Each input cell re-derives one claim.", "Text"],
   Cell["Simplify[Sum[1/n^2, {n, 1, Infinity}] - Pi^2/6]", "Input"],
   Cell[BoxData[ToBoxes[0]], "Output"]}];
Export["derivation.nb", nb];
```

- Input cells as plain strings (`Cell["code", "Input"]`) are the robust
  form; the front end parses them on first evaluation. Reserve BoxData
  for precomputed Output cells (via ToBoxes) so the reader sees results
  without evaluating.
- Useful styles: "Title", "Section", "Subsection", "Text", "Input",
  "Output", "Item".
- Reading one back headlessly: `Import["file.nb", "Notebook"]` returns
  the Notebook expression; the file is also greppable text.
- **Never ship an unverified notebook.** A headless kernel cannot
  faithfully execute a notebook, so every computation a notebook shows
  must have a plain .wls mirror the kernel actually runs, with the
  mirror's PASS log as the evidence - and the mirror must check its
  CHECK COUNT, not just its failure count, since a wiped session
  reports zero failures while running nothing. Generate notebook and
  mirror from one source (a small Python or .wls builder) so they
  cannot drift.
