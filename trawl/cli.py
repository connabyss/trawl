"""The `trawl` command.

  trawl run  prog.trawl     run with the reference interpreter (checks for stuck loops)
  trawl fast prog.trawl     build natively and run (the speed you want for real searches)
                            --jobs N: sweeps on N cores; --save FILE: resume a long run
  trawl build prog.trawl    write a native program next to the source (prog, or prog.exe)
  trawl c    prog.trawl     print the generated C
  trawl verify run.receipt  re-run a receipt (--receipt FILE on run or fast) and check its output
  trawl repl                type Trawl and see the stack after each line
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time

from . import __version__
from .lang import TrawlError, parse, read_source

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)  # numbers of any size, also in the compiler's constants


def folder_error(path):
    return TrawlError(f"{path} is a folder, not a Trawl program: name one .trawl file in it")


def load(path):
    """Read and parse the program at path. A file that can't be read gets a plain message, not Python's."""
    if os.path.isdir(path):
        raise folder_error(path)
    try:
        src = read_source(path)
    except FileNotFoundError:
        raise TrawlError(f"can't open {path}: there's no file by that name") from None
    except OSError as e:
        raise TrawlError(f"can't open {path}: {e.strerror or e}") from None
    return parse(src, path)


def program_paths(source):
    """The program and every library it uses, so no output file can land on any of them."""
    used = []
    try:
        parse(read_source(source), source, used=used)
    except (TrawlError, OSError):
        pass  # the run itself will say what's wrong with it
    return [source] + used


def check_output(path, sources, flag):
    """Refuse an output file that would replace the program or a library it uses, or that has nowhere to go,
    before any work."""
    if path is None:
        return
    if path == "":
        raise TrawlError(f"`{flag}` needs a file name")
    if os.path.isdir(path):
        raise TrawlError(f"`{flag} {path}` is a folder. give a file name")
    for i, src in enumerate(sources):
        if os.path.exists(path) and os.path.exists(src) and os.path.samefile(path, src):
            what = "your program" if i == 0 else f"{os.path.basename(src)}, a library your program uses"
            raise TrawlError(f"`{flag} {path}` would write over {what}. pick another file name")
    folder = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(folder):
        raise TrawlError(f"`{flag} {path}`: there is no folder {folder}")


def check_save(path):
    """--save may only replace a Trawl save file (or nothing): never notes, code or anything else."""
    if path and os.path.isfile(path) and os.path.getsize(path):
        with open(path, "rb") as fh:
            if not fh.read(11) == b"trawl-save ":
                raise TrawlError(f"`--save {path}`: that file isn't a Trawl save file, and a run would write over "
                                 "it. pick a new file name")


EXE_MAGIC = (b"\x7fELF", b"MZ", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe")


def check_kind(path, flag, ok, what):
    """An output may replace an earlier output of the same kind (or nothing), never anything else."""
    if path and os.path.isfile(path) and os.path.getsize(path):
        with open(path, "rb") as fh:
            head = fh.read(64)
        if not ok(head):
            raise TrawlError(f"`{flag} {path}`: that file isn't {what}, and this would write over it. "
                             "pick a new file name")


def child_code(code):
    """The exit code to pass on from the native program: a reader that stopped early (`| head`) is fine, as on
    `trawl run`, and a signal becomes the shell's 128 + its number instead of a wrapped negative."""
    import signal
    if code < 0:
        return 0 if -code == getattr(signal, "SIGPIPE", -1) else 128 - code
    return code


def is_receipt(path):
    from .receipt import read_receipt
    try:
        read_receipt(path)
        return True
    except TrawlError:
        return False


def check_receipt(path):
    if path and os.path.isfile(path) and os.path.getsize(path) and not is_receipt(path):
        raise TrawlError(f"`--receipt {path}`: that file isn't a Trawl receipt, and this would write over it. "
                         "pick a new file name")


TRAWL_MARK = b"made by the Trawl compiler"  # in every program Trawl builds (see rt_usage in trawl_rt.h)


def check_exe(path, flag="-o"):
    """-o may replace a program Trawl built, never another program (or anything else)."""
    if path and os.path.isfile(path) and os.path.getsize(path):
        with open(path, "rb") as fh:
            data = fh.read(64 << 20)
        # older Trawl builds carry no mark, but they do carry their save-file header
        if not (data.startswith(EXE_MAGIC) and (TRAWL_MARK in data or b"trawl-save " in data)):
            raise TrawlError(f"`{flag} {path}`: that file isn't a program Trawl built, and this would write over "
                             "it. pick a new file name")


def check_c(path):
    check_kind(path, "--keep-c", lambda h: h.startswith(b"/* made by the Trawl compiler"), "C that Trawl wrote")


def check_steps(n):
    if n < 1:
        raise TrawlError(f"--max-steps needs a number of steps above 0, not {n}")


def exe_name(path):
    base = os.path.splitext(path)[0]
    return base + (".exe" if os.name == "nt" else "")


def cmd_run(args):
    from .interp import run
    from .progress import Ticker
    check_steps(args.max_steps)
    check_output(args.receipt, program_paths(args.file), "--receipt")
    check_receipt(args.receipt)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # the same bytes the native build writes, on any console
    if args.receipt:
        from .receipt import Tee, program_files, write_receipt
        prog, files, main = program_files(args.file)
        real, t0 = sys.stdout, time.time()
        tee = Tee(real)
        with Ticker(out=tee) as ticker:
            sys.stdout = ticker if ticker.enabled else tee
            try:
                _run_and_print(run, prog, args)
            finally:
                sys.stdout = real
        write_receipt(args.receipt, files=files, main=main, engine="run", output=tee.data(), seconds=time.time() - t0)
        ticker.done()
        print(f"~ receipt written to {args.receipt}", file=sys.stderr)
        return
    prog, real = load(args.file), sys.stdout
    with Ticker() as ticker:
        sys.stdout = ticker if ticker.enabled else real
        try:
            _run_and_print(run, prog, args)
        finally:
            sys.stdout = real
    ticker.done()


def _run_and_print(run, prog, args):
    out, sunk = run(prog, max_steps=args.max_steps, stream=None if sunk_mode(prog) else sys.stdout)
    if sunk is None:
        sys.stdout.write(out + "\n")
    else:
        print(out)
        print(f"({sunk} worlds sank along the way)")


def sunk_mode(prog):
    from .interp import uses_worlds
    return uses_worlds(prog)


def cmd_build(args):
    from .cgen import build
    if args.output == "":
        raise TrawlError("`-o` needs a file name")
    if os.path.isdir(args.file):
        raise folder_error(args.file)
    out = args.output or exe_name(args.file)
    paths = program_paths(args.file)
    if args.output is None and os.path.abspath(out) == os.path.abspath(args.file):
        raise TrawlError(f"the program built from {args.file} would be called {out}, the same name. "
                         "pick a name for it with -o")
    check_output(out, paths, "-o")
    check_exe(out)
    check_output(args.keep_c, paths, "--keep-c")
    check_c(args.keep_c)
    if args.keep_c is not None and os.path.abspath(args.keep_c) == os.path.abspath(out):
        raise TrawlError("`-o` and `--keep-c` name the same file. give the C file its own name")
    prog = load(args.file)
    build(prog, out, args.file, keep_c=args.keep_c)
    print(f"built {out}")


def cmd_fast(args):
    from .cgen import build
    paths = program_paths(args.file)
    check_output(args.receipt, paths, "--receipt")
    check_output(args.save, paths, "--save")
    check_save(args.save)
    check_receipt(args.receipt)
    if args.save and args.receipt and os.path.abspath(args.save) == os.path.abspath(args.receipt):
        raise TrawlError("`--save` and `--receipt` name the same file. give each its own name")
    if args.receipt:
        from .receipt import program_files
        prog, files, main = program_files(args.file)
    else:
        prog = load(args.file)
    with tempfile.TemporaryDirectory() as tmp:
        exe = os.path.join(tmp, "prog" + (".exe" if os.name == "nt" else ""))
        build(prog, exe, args.file)
        sys.stdout.flush()
        extra = []
        if args.jobs is not None:
            extra += ["--jobs", str(args.jobs)]
        if args.save:
            extra += ["--save", os.path.abspath(args.save)]
        from .progress import Ticker
        from .receipt import run_native_teed, write_receipt
        ticker = Ticker()
        if not args.receipt:
            if not ticker.enabled:
                sys.exit(child_code(subprocess.call([exe] + extra)))
            with ticker:
                code, _ = run_native_teed([exe] + extra, ticker=ticker, keep=False)
            if code == 0:
                ticker.done()
            sys.exit(child_code(code))
        t0 = time.time()
        with ticker:
            code, output = run_native_teed([exe] + extra, ticker=ticker if ticker.enabled else None)
        if code != 0:
            print("~ no receipt: the run stopped with an error", file=sys.stderr)
            sys.exit(child_code(code) or 1)
        write_receipt(args.receipt, files=files, main=main, engine="fast", output=output, seconds=time.time() - t0,
                      jobs=args.jobs, save=args.save)
        ticker.done()
        print(f"~ receipt written to {args.receipt}", file=sys.stderr)


def cmd_verify(args):
    from .receipt import verify
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # a console that can't show ✓ gets ? instead of a crash
    check_steps(args.max_steps)
    ok = verify(args.receipt, engine=args.engine, save=args.save, sample=args.sample, max_steps=args.max_steps,
                seed=args.seed)
    sys.exit(0 if ok else 1)


def cmd_c(args):
    from .cgen import to_c
    sys.stdout.write(to_c(load(args.file), args.file))


def cmd_repl(args):
    from .interp import TOO_DEEP, Sea, _deep
    sea, n = Sea(), 0
    color = sys.stdout.isatty()
    dim, red, off = ("\033[2m", "\033[1;91m", "\033[0m") if color else ("", "", "")
    print(f"Trawl {__version__}. the sea is calm. try: use stdlib 10 fib .   (ctrl+d to leave)")
    while True:
        try:
            line = input(f"trawl[{n}]> ")
        except (EOFError, KeyboardInterrupt):
            print("\nthe tide goes out. bye.")
            return
        n += 1
        sea.out, saved, sea.steps, limit = [], list(sea.stack), 0, sea.max_steps

        def stop():  # Ctrl+C: the line stops at its next step, and the sea keeps its words
            sea.max_steps = -1

        try:
            try:
                _deep(lambda: sea.run(parse(line)), on_interrupt=stop)
            except RecursionError:
                raise TrawlError(TOO_DEEP) from None
            print("".join(sea.out) + ("  " if sea.out else "") + dim + str(sea.stack) + off)
        except KeyboardInterrupt:
            sea.stack = saved
            print(f"{red}~ stopped (Ctrl+C){off}  {dim}(stack put back: {saved}){off}")
        except TrawlError as e:
            sea.stack = saved
            print(f"{red}~ {e}{off}  {dim}(stack put back: {saved}){off}")
        finally:
            sea.max_steps = limit


def make_parser():
    p = argparse.ArgumentParser(prog="trawl", description="Trawl: a language for hunting patterns in the integers.")
    p.add_argument("--version", action="version", version=f"trawl {__version__}")
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("run", help="run with the reference interpreter")
    r.add_argument("file", help="the program to run")
    r.add_argument("--max-steps", type=int, default=50_000_000, metavar="N",
                   help="give up after N steps (default: 50 million)")
    r.add_argument("--receipt", metavar="FILE", help="write a receipt of this run (check it with trawl verify)")
    r.set_defaults(fn=cmd_run)
    f = sub.add_parser("fast", help="build natively and run")
    f.add_argument("file", help="the program to build and run")
    f.add_argument("-j", "--jobs", type=int, help="run each top-level sweep on this many cores (0 = all)")
    f.add_argument("--save", metavar="FILE", help="keep finished sweep blocks in FILE; the same command again resumes")
    f.add_argument("--receipt", metavar="FILE", help="write a receipt of this run (check it with trawl verify)")
    f.set_defaults(fn=cmd_fast)
    v = sub.add_parser("verify", help="re-run a receipt and check the output matches")
    v.add_argument("receipt", help="the receipt to check, written by --receipt")
    v.add_argument("--engine", choices=["run", "fast"], help="engine to re-run on (default: the other one)")
    v.add_argument("--save", metavar="FILE", help="the run's save file: replay it, re-running --sample blocks")
    v.add_argument("--sample", type=int, default=0, metavar="N", help="with --save: blocks of each sweep to re-run")
    v.add_argument("--seed", type=int, help="with --save: pick the same blocks again")
    v.add_argument("--max-steps", type=int, default=50_000_000, metavar="N",
                   help="when re-running on the reference interpreter: give up after N steps (default: 50 million)")
    v.set_defaults(fn=cmd_verify)
    b = sub.add_parser("build", help="build a native program")
    b.add_argument("file", help="the program to build")
    b.add_argument("-o", "--output", metavar="FILE",
                   help="where to write the program (default: the program's name without its extension, "
                        "plus .exe on Windows)")
    b.add_argument("--keep-c", metavar="FILE", help="also save the generated C to FILE")
    b.set_defaults(fn=cmd_build)
    c = sub.add_parser("c", help="print the generated C")
    c.add_argument("file", help="the program to turn into C")
    c.set_defaults(fn=cmd_c)
    q = sub.add_parser("repl", help="interactive sea")
    q.set_defaults(fn=cmd_repl)
    return p


def main(argv=None):
    p = make_parser()
    for name in ("stdout", "stderr"):  # started with that stream closed (`trawl run x >&-`): write nowhere
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
    args = p.parse_args(argv)
    if not args.cmd:
        if not sys.stdin.isatty():
            p.print_help()
            return
        args.fn = cmd_repl
    from .interp import _deep
    try:
        try:
            if args.fn is cmd_repl:
                cmd_repl(args)  # each line gets its own big stack, so Ctrl+C can stop just that line
            else:
                _deep(lambda: args.fn(args))  # a big stack: deep words and deeply nested brackets both fit
        except RecursionError:
            raise TrawlError("the program nests too deep: brackets or words inside each other "
                             "thousands of levels down") from None
    except TrawlError as e:
        sys.stdout.flush()
        sys.exit(f"~ {e}")
    except BrokenPipeError:  # `trawl run x | head` stopped reading: that's fine, stop quietly
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except OSError:
            pass
        sys.exit(0)
    except OSError as e:
        sys.exit(f"~ {e}")
    except KeyboardInterrupt:
        sys.stdout.flush()
        print("\n~ stopped (Ctrl+C)", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
