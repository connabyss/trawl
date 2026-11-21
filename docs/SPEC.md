# The Trawl language

Version 0.1. This page is the definition of Trawl. Where the two engines could ever
disagree, the reference interpreter (`trawl run`) is right, and the native compiler
(`trawl fast`, `trawl build`) has a bug.

Trawl began as Tide, a language two Claude agents made up for fun in a Codespace, which
they then used to explore patterns in the integers. Every Tide program runs unchanged in Trawl and prints the same thing.

## 1. Reading a program

A program is text. It is split into **tokens** at whitespace. There are four kinds:

| Token | Looks like | Meaning |
|---|---|---|
| number | `42`, `-7`, `+3`, `1_000_000` | push that whole number |
| text | `." hello sea"` | print the text (leading spaces after `."` are dropped) |
| word | `dup`, `digsum`, `my-word` | do what the word says |
| structure | `:` `;` `[` `]` `if` `else` `then` `use` `pearl` `sweep` | shape the program |

- `#` starts a comment that runs to the end of the line, **except** on a line that also
  contains `."` text. (This keeps `#` usable inside printed text. Put comments on their
  own lines when a line prints something.)
- Words are case-sensitive and can contain any characters except whitespace and `#`
  (which starts a comment).
- Number literals can be any size.

## 2. Numbers

Every value is a whole number of unlimited size. There are no fractions, floats, strings
or booleans. Comparisons give `1` for true and `0` for false; `if` and loops treat any
nonzero number as true.

- `/` rounds toward minus infinity and `%` takes the sign of the divisor (so
  `-7 2 /` is `-4` and `-7 2 %` is `1`). For any `a` and nonzero `b`:
  `a = (a b /) * b + (a b %)`.
- Dividing by zero is an error.

## 3. The stack

Words take their inputs from the top of the stack and leave their results there. Stack
effects are written `( before -- after )`, top of the stack on the right.

| Word | Effect | |
|---|---|---|
| `dup` | `( a -- a a )` | |
| `drop` | `( a -- )` | |
| `swap` | `( a b -- b a )` | |
| `over` | `( a b -- a b a )` | |
| `rot` | `( a b c -- b c a )` | |
| `fold` | `( ... -- reversed ... )` | reverses the whole stack |
| `depth` | `( -- n )` | how many numbers are on the stack |

## 4. Arithmetic and comparison

| Word | Effect |
|---|---|
| `+ - *` | `( a b -- a+b )`, `( a b -- a-b )`, `( a b -- a*b )` |
| `/ %` | `( a b -- floor(a/b) )`, `( a b -- a mod b )` |
| `= < >` | `( a b -- flag )` |
| `power` | `( a k -- a^k )`, `k >= 0` (`0 0 power` is 1). An answer that is surely over 2^34 bits (about 5 billion digits) is refused; the check counts the base's bits roughly, so one up to twice that size may still be tried and run out of memory |
| `prime` | `( n -- flag )` 1 if `n` is prime, else 0 (0 for `n < 2`). Exact below 3317044064679887385961981 ≈ 3.3·10^24 (strong probable-prime tests to the first 13 primes, which no composite below that passes; that number is the first one that does). From there up it tests to the first 20 primes, so that number is caught, but it is a probable-prime test: right for any number you're likely to meet, though a composite built on purpose to fool all 20 tests would pass |
| `spf` | `( n -- p )` the smallest prime factor of `n` (`n >= 2`; `n` itself when `n` is prime, by the same test as `prime`). Fast when `n` has a small prime factor; a number whose two smallest prime factors both have 15 or more digits takes seconds, and 20 or more digits can take a very long time |
| `factorings` | `( n -- count )` how many ways `n` is a product of whole numbers above 1, order ignored (OEIS A001055; `n >= 1`, and `1 factorings` is 1). `12 factorings` is 4: 12, 2·6, 3·4, 2·2·3. It factors `n` (as `spf` does) and counts from the exponents alone, remembering every exponent pattern it has counted. Exact for any size; slow when `n` has many distinct prime factors with large exponents |

## 5. Digits in any base

These are Trawl's own words, the ones the research ran on.

| Word | Effect | |
|---|---|---|
| `digsum` | `( x base -- s )` | sum of the digits of `abs(x)` in `base` (`base >= 2`). Always matches `abs(x)` mod `base - 1`. |
| `altsum` | `( x base -- s )` | units - tens + hundreds - ... of `abs(x)`. Always matches `abs(x)` mod `base + 1`. |

`1234 10 digsum` is 10. `1234 10 altsum` is 2. `255 2 digsum` is 8 (the number of 1 bits).

## 6. Printing

| Word | Effect | Prints |
|---|---|---|
| `.` | `( a -- )` | the number and a space |
| `emit` | `( c -- )` | the character with that code (UTF-8) |
| `." text"` | `( -- )` | the text |
| `.s` | `( -- )` | the stack, like `<1 2 3> ` |
| `.bed` | `( -- )` | the nonzero seabed cells, like `{7:42 9:1} ` |
| `.pearls` | `( -- )` | how many answers the pearls remember, like `(12 pearls) ` |

When a program finishes, a newline is printed.

## 7. Control

- `cond if A then` runs `A` when `cond` is nonzero. `cond if A else B then` picks one.
  `if` removes `cond`.
- `[ A ]` is a loop: **while the top of the stack is nonzero, run `A`**. The top is
  checked, not removed. An empty stack ends the loop. So the usual shapes are:

```
cond [ drop  A  cond ] drop        # while cond: A
1 [ drop  A  cond ] drop           # do A, repeat while cond
```

## 8. Words of your own

`: name body ;` defines a word. Words can call themselves and each other. A word can be
defined again later; from then on the new meaning is used, also by words defined before it.
A word that is called before any definition of it has run is an error, at that moment.
Built-in words can't be redefined, except `prime`, `spf` and `factorings`: your own
definition of one of those takes over from the point it runs. A number can't be a word's name.

```
: sq dup * ;
: fact dup 2 < if drop 1 else dup 1 - fact * then ;
```

`use name` reads `name.trawl` (or `name.tide`) right there, from the program's own folder
or from the standard library. See [STDLIB.md](STDLIB.md).

## 9. The seabed

The seabed is memory: numbered cells, every one starting at 0. Addresses are any whole
number (the native build needs them below 2^62 in size).

| Word | Effect | |
|---|---|---|
| `bury` | `( value addr -- )` | store `value` at `addr` |
| `dig` | `( addr -- value )` | read the cell (0 if never set) |
| `drain` | `( -- )` | set every cell back to 0 |

By habit, small negative addresses are used as named variables (`-7 dig`, `5 -7 bury`)
and positive ranges as arrays. The native compiler is built around that habit: cells at
fixed addresses inside loops are kept in CPU registers.

## 10. Echo: has this happened before?

| Word | Effect | |
|---|---|---|
| `echo` | `( lo hi -- k )` | look at seabed cells `lo..hi`. If they have looked exactly like this at an earlier `echo`, push how many echoes ago that was (the length of the loop); otherwise push 0. Either way, remember this picture. At most 16777216 cells at once. |
| `hush` | `( -- )` | forget every picture |

With `echo`, a program can find for itself when a system (a reef, a deck, a ferry) starts
repeating, and how long the repeat is.

## 11. Worlds: guess, and rewind when wrong

| Word | Effect | |
|---|---|---|
| `wave` | `( lo hi -- x )` | guess a number from `lo` to `hi` |
| `want` | `( flag -- )` | if `flag` is 0 this world is wrong: it sinks, and the sea rewinds to the last guess and tries its next number |
| `more` | `( -- )` | keep what this world printed, then sink it anyway to find the next world |
| `aim` | `( score -- )` | remember this world and its score, then sink it; when the guesses run out, what the lowest-scoring world printed is shown (ties go to the first). A world that reaches the end of the program instead stops the search there, and only what was kept with `more` and that world's own output are shown |
| `worlds` | `( -- n )` | how many worlds have sunk so far |

Each world replays the program from the start in a fresh sea (empty stack, empty seabed,
no echoes, no pearls), following the guesses so far. A program that uses these words
prints what its worlds kept, then a line `(N worlds sank along the way)`. If every world
sinks and none was kept or aimed, that is an error. After 2,000,000 sunk worlds the search
stops with an error.

```
: queen 1 4 wave ;   # ... want ... more     (see examples/queens.trawl)
```

## 12. Pearls: remembered answers

`pearl name` makes the word `name` remember answers. A pearled word must take one number
and leave one (a run stops with an error the first time it doesn't); after `pearl name`, asking it the same number again gives the remembered
answer without running it. Pearls work through recursion, so
`: fib dup 2 < if else dup 1 - fib swap 2 - fib + then ; pearl fib` makes `90 fib` instant.

## 13. Sweep: every n, on every core

`lo hi sweep name` runs the word `name` on every n from `lo` up to `hi - 1`, in order, and
leaves how many of them gave a nonzero answer. `name` must be one of your own words, it must
turn n into exactly one number (its answer), and it must not touch the stack below n.
Anything it prints comes out in n order. `lo >= hi` sweeps nothing and leaves 0. Both ends
must lie between -2^62 and 2^62 - 1. Built-ins that take one number and leave one,
such as `prime`, can be wrapped in your own word: `: prime? prime ;` followed by
`1 1000 sweep prime? .`.

```
: sq? dup * 1 + prime ;
1 100 sweep sq? .     # 19: the n below 100 with n^2 + 1 prime
```

`sweep` is how a search says "these checks don't depend on each other", so the native
engine can share them out and pick them up again:

- **`--jobs N`** runs each sweep on N cores (`0` means all of them):
  `trawl fast hunt.trawl --jobs 8`, or `./hunt --jobs 8` for a built program. The range is cut
  into 256 blocks; each block runs in its own copy of the sea, and its printed words come out
  in n order, so the output is exactly what one core prints.
- **`--save FILE`** writes each finished block (its count and its printed words) to FILE.
  Stop the run at any point and start the same command again: finished blocks are replayed
  from FILE, and only the rest are run. FILE only resumes the program that wrote it; a changed
  program starts over (and says so). Each block carries a check of its own, so a block
  damaged on disk runs again, along with every block after it. `--save` never writes over a
  file that isn't a Trawl save file.

**The rule that makes this safe:** a block's changes to the seabed, to pearls, to what
`echo` remembers, to the words it defines and to the stack below n stay in its own copy of the sea. They may or may not be seen by later calls, or after the sweep. So a
swept word should set every seabed cell it reads before it reads it. Scratch cells are fine;
a running total kept in the seabed across calls is not (use the count, or print the finds).

Only sweeps that are not inside another sweep are shared out; a sweep inside a swept word
just runs. Programs that use worlds (`wave`, `want`, `more`, `aim`) run their sweeps on one
core without saving. On Windows, which has no `fork`, `--jobs` runs on one core. The
interpreter (`trawl run`) always runs sweeps in order, on one core.

## 14. Errors

Errors stop the program and print one line starting with `~`. The wording is part of the
language and the same in both engines, for example:

- `the tide went out too far: `+` wanted 2 numbers, but the shore ran out`
- `you tried to split 7 into zero pieces. the ocean refuses.`
- `base 1 has no digits. try 2 or more.`
- `tide numbers are whole: 2 to the power -1 would be a fraction`
- `that power is too big for the sea to hold`
- `the sea ran out of memory`
- `nobody in the sea knows the word `flod`. did you mean `fold`?`
- `` `sweep two` wants `two` to turn each n into one answer, but at n = 1 it left 2 numbers in its place``
- `the tide is stuck: this loop came back to the exact same sea [...], so it can never end` (interpreter only, see below)
- `the sea got too deep: words called inside words too many levels down. does a word call itself forever?` (interpreter only, see below)

## 15. The two engines

**`trawl run`** (reference interpreter, Python) checks two extra things:

- **Stuck loops.** Trawl is deterministic, so a loop that comes back to the exact same sea
  will repeat forever. The interpreter remembers what the sea looked like at the top of each
  pass and stops with a proof when a picture repeats. The picture is everything a pass can
  see: the stack, the seabed, every definition run so far (a word defined again changes
  the picture), what pearls remember, what `echo` remembers and where `wave` is on its guesses. It is only taken while stack, seabed and `echo`'s memory hold at most 256
  numbers between them; a bigger sea, or a loop that never repeats exactly (one that calls
  `echo` or `wave` each pass never does), runs until the step limit stops it.
- **A step limit** (50 million by default; `--max-steps N`).

**`trawl fast` / `trawl build`** (native compiler, through C) skip both checks, for speed.
They also differ in a few edges that don't change any correct program's output:

- Output is printed as the program runs (the interpreter in worlds mode collects it).
- Seabed addresses must be smaller than 2^62 in size.
- Words calling words: both engines stop with `the sea got too deep` thousands of levels
  down (the native build at exactly 25,000; the interpreter's limit depends on the words:
  about 25,000 to 40,000 for plain words, as few as about 16,000 for long words full of `if`s or loops).
- A word with loops nested hundreds deep takes the C compiler a long time (seconds to minutes)
  to build; the interpreter starts it at once.

Without the stuck-loop check and the step limit, a stuck loop makes a native build run forever, so
try a new program on `trawl run` first. Everything else (results, printed text, error
messages) is the same, and the test suite
checks that on every example and every old Tide program.
