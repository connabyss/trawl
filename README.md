# Trawl

**A small language for searching for patterns in the integers.** Iterate a rule, watch where it
goes, find the loops, search for the first number with a property. Every number is an exact
whole number of any size. Loops prove when they are stuck, one word detects when the state
repeats, and searches can guess and rewind. A native compiler (through C) makes the long
searches fast.

<p align="center"><img src="media/search.svg" width="760" alt="trawl fast prints the first eight terms of OEIS A343507, from Erdős problem 727, in about 10 seconds of real time. a(10) to a(12) were found in November 2026 and are now in the OEIS."></p>

## Try it in 30 seconds

```
git clone https://github.com/connabyss/trawl && cd trawl
pip install .
```

Save this as `rivers.trawl`. It follows the rule x -> x + (digit sum of x)^2:

```
: flow dup 10 digsum dup * + ;
1 15 [ swap dup . flow swap 1 - ] drop drop
```

```
$ trawl run rivers.trawl
1 2 6 42 78 303 339 564 789 1365 1590 1815 2040 2076 2301
```

`trawl fast rivers.trawl` prints the same thing, compiled to machine code first.
Or skip the install: download [playground/index.html](playground/index.html) and open it in a browser. It runs Trawl right in the page (it fetches Python for the browser, Pyodide, the first time, so it needs the internet).
You need Python 3.10 or newer, and gcc or clang for `trawl fast` and `trawl build`
(on Windows: [w64devkit](https://github.com/skeeto/w64devkit) or MSYS2). Typing `trawl`
alone in a terminal opens an interactive prompt (`trawl repl` does the same anywhere).

## Where it came from: Erdős problem 727

[OEIS A343507](https://oeis.org/A343507) asks, for each n, for the least k such that
((k+n)!)^2 divides (2k)!. It comes from [Erdős problem 727](https://www.erdosproblems.com/727).
Daniel Mizrahi found the first nine terms in 2021 with his own C program, up to
a(9) = 2935782889, and the table stopped there for five years.

Trawl didn't start with this problem. connabyss gave a few Claude agents a GitHub Codespace and
told them to go wild. For fun, two of them made up a tiny stack language, Tide, and used it
to poke at whatever interested them, which drifted toward odd patterns in the integers. On
November 14, 2026, connabyss pointed them at real, famous open problems, this one among them.
Their C searches found three more terms, and each was checked again with separate code:

| | least k | found and checked | reproduced by the Trawl search |
|---|---|---|---|
| a(10) | 19295451536 | yes | yes, in 8 minutes |
| a(11) | 91328826321 | yes | yes, in 33 minutes |
| a(12) | 1490709825264 | yes | yes, in about 5 hours on 6 cores |

**These terms are now in the OEIS.** connabyss submitted them, and OEIS editors reviewed and
approved them on November 15, 2026: see [A343507](https://oeis.org/A343507).

Trawl is Tide grown into a real language: a written spec, a test suite, a standard library
and a native compiler. The search in [examples/a343507.trawl](examples/a343507.trawl) finds
a(10) and a(11) on its own: add `10 2935782889 19300000000 search .` at its bottom and run it with
`trawl fast` (about 8 minutes on one core). For a(12), the range from a(11) to 1490800000000 was split into
six pieces, one per core of an i5-10600K, each run with `trawl fast --receipt`: the five lower pieces printed 0
and the top one printed 1490709825264 (about 27 core-hours in all). That run also found a bug: past about
5·10^11 the example's prime sieve wrote over its own prime table and looped forever (fixed in
[#37](https://github.com/connabyss/trawl/pull/37)). The open problem itself is in
[examples/erdos727](examples/erdos727): Johan Land's k = 3 family and a k = 4 family found by
a research Claude (a lead, not a proof). On the same slice of the search, it runs about 3 to 4 times slower
than the hand-written C, 8 to 10 times faster than plain Python (it varies by machine), and 170 times faster than the
original Tide engine ([docs/BENCHMARK.md](docs/BENCHMARK.md)). The 97 old Tide programs in the test suite
still run and print exactly what they printed before.

**More finds, reproduced in Trawl.** [examples/a398813.trawl](examples/a398813.trawl) finds
the terms of [A398813](https://oeis.org/A398813) with the `factorings` built-in, then checks
every candidate up to 2^31·3^14·5^12 = 2507653251072000000000000 on all cores: it is the
smallest number that takes 7 steps to reach 1 (that a(7) is submitted and waiting for an OEIS
editor's review). [examples/spiral_packing.trawl](examples/spiral_packing.trawl) computes
the greedy packing coloring of the grid in spiral order (A402223, a new sequence submitted
to the OEIS and waiting for an editor's review), and the cells where each new largest value first appears, up to 32 at cell 3355518. Run both with
`trawl fast`: they are too long for the interpreter's step limit. Add
`--receipt FILE` to either run and anyone can check it with `trawl verify`.

**Who made it.** Trawl was designed and written by Claude agents (Anthropic's AI), directed
by connabyss. The core syntax comes from Forth, and [docs/PRIOR_ART.md](docs/PRIOR_ART.md)
says plainly what is borrowed and what is new.

## A quick tour

Numbers go on a stack; words take from it and give back.

```
2 3 + 4 * .            # 20
: sq dup * ;  12 sq .  # 144
2 100 power .          # 1267650600228229401496703205376 (never overflows)
1234 10 digsum .       # 10, the digit sum in base 10
1234 10 altsum .       # 2,  units - tens + hundreds - ...
600851475143 spf .     # 71, the smallest prime factor (built in, fast up to about 30 digits)
12 factorings .        # 4: 12 = 2*6 = 3*4 = 2*2*3, products in any order counted once
42 7 bury  7 dig .     # 42: the seabed is memory with numbered cells
5 [ dup . 1 - ] drop   # 5 4 3 2 1: a loop runs while the top is nonzero
```

The words that make Trawl what it is:

| | |
|---|---|
| **stuck loops** | `trawl run` stops a loop that comes back to exactly the same state (stack, memory and all, while that is at most 256 numbers), with proof that it would never end, instead of hanging. Bigger or never-repeating loops hit the step limit instead; `trawl fast` skips the check |
| `echo` | `lo hi echo` asks: have seabed cells lo..hi looked exactly like this before? It gives how many looks ago (the loop length), or 0 |
| `wave` `want` `more` `aim` | `1 9 wave` guesses a number; `want` rewinds to try the next guess when a condition fails; `more` collects every answer; `aim` keeps the best |
| `pearl` | `pearl fib` makes a word remember its answers |
| `digsum` `altsum` | digit sums in any base |
| `sweep` | `1 1000000 sweep good?` runs `good?` on every n and counts the hits. Built programs share it out with `--jobs 8` (same output, in order) and pick a stopped run back up with `--save run.sav` |
| `prime` `spf` | primality and the smallest prime factor, built in and fast: with them the Erdős 727 k = 4 search runs 14 times faster than the same search in PARI/GP, which uses its general `factor()` ([benchmarks/vs](benchmarks/vs); different tools, same 157 answers) |
| `factorings` | how many ways a number factors, order ignored (OEIS A001055), exact at any size |

```
: step dup * 31 % ;    # the rule x -> x^2 mod 31
use orbits
3 orbit . .            # 4 1: falls into a loop of length 4 after 1 step
```

The full definition is in [docs/SPEC.md](docs/SPEC.md), the library in
[docs/STDLIB.md](docs/STDLIB.md), and what Trawl borrows from Forth and others (and what
it adds) in [docs/PRIOR_ART.md](docs/PRIOR_ART.md).

## Two engines, one answer

- **`trawl run`** is the reference interpreter, in Python. It checks for stuck loops and has
  a step limit. It defines what Trawl means.
- **`trawl fast` / `trawl build`** compile to C and then to machine code. Numbers are
  62-bit machine words that turn into exact big numbers when they overflow, so the output
  is the same as the interpreter's (the few edges where they differ, like seabed addresses
  of 2^62 and up, are listed in [docs/SPEC.md](docs/SPEC.md) section 15). Seabed cells at fixed addresses (the usual way to
  keep variables) live in CPU registers inside loops.

The test suite checks that both engines print exactly the same thing, and that all 97
Tide programs kept from the original research print exactly what the old Tide engine printed.

## Receipts: check a result without trusting the run

Add `--receipt FILE` to `trawl run` or `trawl fast`, and the run leaves a small JSON file
behind. It holds the program and every library it used (the full text), the Trawl version,
how the program was run, and the SHA-256 of exactly what it printed. Anyone with the
receipt can check it:

```
trawl fast hunt.trawl --receipt hunt.receipt
trawl verify hunt.receipt        # re-runs it on the other engine and compares, byte for byte
```

A native run is re-checked by the reference interpreter by default, so a compiler bug can't
vouch for itself (`--engine fast` re-runs it natively instead, for speed). A long sweep is
too slow for the interpreter, so a saved run can be spot-checked instead:

```
trawl fast hunt.trawl --jobs 8 --save hunt.sav --receipt hunt.receipt
trawl verify hunt.receipt --save hunt.sav --sample 8
```

This re-runs 8 random blocks of every sweep on the interpreter and checks them against
the saved ones. Every other block is replayed from the save file, and the whole output must
still match the receipt. A spot check is evidence, not proof: it catches a wrong block only
if it happens to pick it, and verify says how many of the blocks it really re-ran.

A re-run takes about as long as the first run did, and verify says how long that was. While
it works, and whenever `trawl run` or `trawl fast` goes quiet for more than a second, the
terminal shows a `still checking... 1:12` line that ticks every second, then `~ done in 2:05`
at the end. The line goes to stderr and only to a terminal, so piped output and receipts are
exactly what the program printed (`TRAWL_PROGRESS=0` turns it off).

To check one of the results above yourself, or to rerun someone else's check, open a case:
[CASES.md](CASES.md) has the steps and the list so far.

## Tests

```
pip install -e .[test]
python -m pytest          # the quick run, about two minutes
python -m pytest --all    # everything, as CI runs it: a few minutes
```

The tests run on Linux, macOS and Windows. New here? See [CONTRIBUTING.md](CONTRIBUTING.md)
and the issues marked **good first issue**.

## License

MIT. See [LICENSE](LICENSE).
