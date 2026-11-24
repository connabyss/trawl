# The standard library

Libraries are Trawl files. `use name` reads `name.trawl` from your program's folder, or
from the library folder that ships with Trawl (`trawl/lib/`).

## stdlib

The original Tide toolbox, written in Tide itself. `use stdlib`

| Word | Effect | |
|---|---|---|
| `nip` | `( a b -- b )` | |
| `tuck` | `( a b -- b a b )` | |
| `sq` | `( a -- a*a )` | |
| `abs` | `( a -- b )` | absolute value |
| `max`, `min` | `( a b -- m )` | |
| `even` | `( a -- flag )` | |
| `fact` | `( n -- n! )` | |
| `fib` | `( n -- F(n) )` | fast, with a loop |
| `slow-fib` | `( n -- F(n) )` | slow on purpose, a good job for pearls |
| `gcd` | `( a b -- g )` | |
| `divides` | `( a b -- flag )` | 1 if b divides a |
| `prime` | `( n -- flag )` | now a built-in word, much faster (see the spec). `use stdlib` still works the same |
| `cr` | `( -- )` | print a newline |

## numbers

Number theory for hunting. `use numbers` (it uses stdlib too).
Working cells: -65535 .. -65280. Leave them alone in your programs.

| Word | Effect | |
|---|---|---|
| `isqrt` | `( n -- r )` | floor of the square root (n >= 0) |
| `vp` | `( n p -- e )` | how many times p divides n (0 for n = 0) |
| `legendre` | `( n p -- e )` | how many times the prime p divides n! |
| `carries` | `( a b p -- c )` | carries when adding a + b in base p, which is the power of p in C(a+b, a) (Kummer) |
| `powmod` | `( b e m -- r )` | b^e mod m |
| `ndigits` | `( x base -- k )` | number of digits (0 has 1) |
| `reverse` | `( x base -- y )` | digits read backwards |
| `smooth` | `( n B -- flag )` | 1 if every prime factor of n is at most B |
| `nextprime` | `( n -- p )` | the smallest prime above n |
| `totient` | `( n -- phi )` | Euler's totient: how many of 1..n share no factor with n (n >= 1) |
| `sigma` | `( n -- s )` | the sum of the divisors of n (n >= 1) |

## orbits

Follow a rule until it comes back around. `use orbits`.
Define the rule first as a word called `step` ( x -- next ).
Working cells: -65279 .. -65270.

| Word | Effect | |
|---|---|---|
| `orbit` | `( x -- tail loop )` | steps before the loop starts, and the loop's length (Brent's method: constant memory, any length) |
| `lands` | `( x -- y )` | the first number of the loop that x falls into |
| `steps` | `( x k -- y )` | apply step k times |

```
: step dup * 31 % ;     # x -> x^2 mod 31
use orbits
3 orbit . .             # prints 4 1: a loop of 4, reached after 1 step
```
