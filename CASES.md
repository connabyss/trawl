# Cases

Trawl's README makes claims: search results, OEIS terms, speed numbers. Each one should hold up when someone else reruns it, ideally with their own code. This page tracks those claims.

## How it works

1. **Open a case** with the [Reproduce or refute](https://github.com/connabyss/trawl/issues/new?template=reproduce-or-refute.yml)
   form: one claim, the exact steps, what should happen, what did happen, and where you ran it.
2. **Rerun someone else's case.** Follow its steps on your own machine and post what you got, same or different,
   with your environment. A different result is as useful as a match.
3. **Close it** with what came of it: a fix, a new result written up, or a refutation. Everyone who opened or reran
   the case is credited in the list below.

Nothing here counts on the word of the person who opened it, including connabyss. Long runs can carry a receipt (`trawl fast --receipt FILE`), and `trawl verify FILE` rechecks one on another machine.

## The counts

**Open 1 · Reproduced 0 · Resolved 0 · Confirmed 0**

- **Open**: the case is still being worked on.
- **Reproduced**: someone other than the person who opened it followed the steps and got the reported behavior or result.
- **Resolved**: the case is closed, with a fix, a written-up result, or a clear refutation.
- **Confirmed**: the original claim held up after that independent check.

The counts are not mutually exclusive. One case can be Reproduced and Confirmed, and still Open until it is written up.
A rerun that gets a different result refutes the claim: that case is never counted as Reproduced or Confirmed, and it
closes as Resolved once the reason is written down.

## The list

| Case | Claim | Opened by | Reproduced by | Status |
|---|---|---|---|---|
| [#?](https://github.com/connabyss/trawl/issues) | The family n = 8t^4 − 18t^2 + 6 gives k = 4 in Erdős problem 727 for exactly 53 values of t below 2000. Rerun: `trawl fast examples/erdos727/run_k4.trawl`, then check with your own code (Legendre's formula is enough). | connabyss | waiting for a rerun | Open |
