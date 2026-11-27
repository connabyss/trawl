# Security

Trawl compiles your programs to C and runs them on your machine (`trawl fast`, `trawl build`). So a bug that
lets a Trawl program escape into the generated C, or crash the compiler in a way that runs other code, matters.
Please tell us about one privately first, not in a public issue.

## How to report one

- Best: the **Report a vulnerability** button on the
  [Security tab](https://github.com/connabyss/trawl/security/advisories/new). Only the maintainer sees it.
- Or email connabyss.code@proton.me with "Trawl security" in the subject.

Say what you ran, what happened, and which commit you're on. A small `.trawl` program that shows it helps most.
You'll get an answer within a week, and credit in the fix if you'd like it.

## Which versions get fixes

Only the newest code on `main`.

## What counts

- A Trawl program that makes the generated C do something its Trawl code doesn't say (like writing outside its
  own memory), or that injects its own C into the build.
- The playground running code from a shared link without you pressing Run.
- A workflow in this repo leaking a secret or running untrusted pull request code with write access.

Not a security hole: a Trawl program that loops forever or uses a lot of memory. That's math. The two engines
disagreeing on an answer is a bug, so open a normal issue for it.
