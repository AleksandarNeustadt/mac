# save as: scan_project_deep.py
import os
import re
import sys
import ast
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set

EXCLUDE_DIRS = {
    "__pycache__", ".git", ".idea", ".vscode", "venv", "env", ".mypy_cache",
    ".pytest_cache", "dist", "build", "node_modules", ".tox", ".eggs"
}
PY_EXT = (".py",)

GITHUB_CHECKLIST = [
    "README.md", "LICENSE", ".gitignore",
    "docs",  # dir
    "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
    "CHANGELOG.md", "pyproject.toml", "requirements.txt", ".gitattributes",
]

TODO_PAT = re.compile(r"\b(TODO|FIXME|XXX)\b", re.IGNORECASE)

def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def count_loc(text: str) -> Tuple[int, int, int]:
    total = 0
    code = 0
    comments = 0
    for line in text.splitlines():
        total += 1
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            comments += 1
        else:
            code += 1
    return total, code, comments

def parse_python(path: Path) -> Dict[str, Any]:
    src = safe_read_text(path)
    info: Dict[str, Any] = {
        "module_doc": None,
        "functions": [],
        "classes": [],
        "globals": [],
        "imports": [],
        "has_main_guard": False,
        "todos": [],
        "uses_print": False,
        "uses_breakpoint": False,
    }

    if not src:
        return info

    # quick flags
    info["todos"] = [m.group(0) for m in TODO_PAT.finditer(src)]
    if "print(" in src:
        info["uses_print"] = True
    if "breakpoint(" in src or "pdb.set_trace(" in src:
        info["uses_breakpoint"] = True

    try:
        tree = ast.parse(src)
    except Exception:
        return info

    info["module_doc"] = ast.get_docstring(tree)

    # module-level assignments (globals)
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = []
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        targets.append(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets.append(node.target.id)
            for name in targets:
                info["globals"].append({
                    "name": name,
                    "lineno": getattr(node, "lineno", None),
                    "is_const_like": name.isupper()
                })

    # imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                info["imports"].append({"type": "import", "module": alias.name})
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                info["imports"].append({"type": "from", "module": mod, "name": alias.name})

    # main guard
    for node in tree.body:
        if isinstance(node, ast.If):
            try:
                cond = ast.unparse(node.test)  # Py3.9+; fallback below if needed
            except Exception:
                cond = ""
            if "__name__" in cond and "__main__" in cond:
                info["has_main_guard"] = True

    # functions (module-level)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info["functions"].append(extract_func(node))

    # classes + methods
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except Exception:
                    bases.append(getattr(b, "id", ""))
            cls = {
                "name": node.name,
                "bases": bases,
                "decorators": [get_dec_name(d) for d in node.decorator_list],
                "doc": ast.get_docstring(node),
                "methods": []
            }
            for n in node.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cls["methods"].append(extract_func(n))
            info["classes"].append(cls)

    return info

def get_dec_name(d: ast.AST) -> str:
    try:
        return ast.unparse(d)
    except Exception:
        if isinstance(d, ast.Name): return d.id
        return d.__class__.__name__

def extract_func(fn: ast.AST) -> Dict[str, Any]:
    args = []
    defaults = []
    decorators = []
    returns = None
    is_async = isinstance(fn, ast.AsyncFunctionDef)

    try:
        decorators = [get_dec_name(d) for d in fn.decorator_list]
    except Exception:
        decorators = []

    try:
        if fn.returns is not None:
            returns = ast.unparse(fn.returns)
    except Exception:
        returns = None

    # args
    params = getattr(fn, "args", None)
    if params:
        for a in params.args:
            args.append(a.arg)
        if params.vararg:
            args.append("*" + params.vararg.arg)
        for a in params.kwonlyargs:
            args.append(a.arg + "=")
        if params.kwarg:
            args.append("**" + params.kwarg.arg)

        # defaults present?
        defaults = ["?"] * (len(params.defaults) + len(params.kw_defaults or []))

    return {
        "name": fn.name,
        "is_async": is_async,
        "args": args,
        "has_defaults": bool(defaults),
        "decorators": decorators,
        "doc": ast.get_docstring(fn)
    }

def walk_project(base: Path) -> Dict[str, Any]:
    base = base.resolve()
    files: List[Path] = []
    for root, dirs, filenames in os.walk(base):
        # filter dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn.endswith(PY_EXT):
                files.append(Path(root) / fn)

    files = sorted(files)
    modules: Dict[str, Any] = {}
    import_edges: Dict[str, Set[str]] = {}
    now = time.time()

    for path in files:
        rel = path.relative_to(base).as_posix()
        module_name = rel[:-3].replace("/", ".")  # rough module name
        text = safe_read_text(path)
        total, code, comments = count_loc(text)
        stat = path.stat()

        parsed = parse_python(path)

        modules[module_name] = {
            "path": rel,
            "size_bytes": stat.st_size,
            "mtime": stat.st_mtime,
            "mtime_human": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "loc_total": total,
            "loc_code": code,
            "loc_comments": comments,
            **parsed
        }

        # build import graph
        deps = set()
        for imp in parsed["imports"]:
            mod = imp.get("module") or ""
            # normalize only likely local imports
            if mod.startswith(".") or mod.split(".")[0] in {"app", "system", "plugins", "tests"}:
                deps.add(mod.split(" as ")[0])
        import_edges[module_name] = deps

    # orphan-ish modules: no one imports them (heuristic)
    reverse: Dict[str, int] = {}
    for src, deps in import_edges.items():
        for d in deps:
            reverse[d] = reverse.get(d, 0) + 1
    orphan_candidates = []
    for m in modules.keys():
        # exclude obvious entry points / dunder / tests / package inits
        rel = modules[m]["path"]
        name = Path(rel).name
        if name in {"__init__.py"} or name.endswith("_test.py") or name.startswith("test_"):
            continue
        if name in {"main.py", "mac.py", "create.py", "scan.py"}:
            continue
        # module key might not match exact import form; keep heuristic
        if reverse.get(m, 0) == 0:
            orphan_candidates.append(m)

    # tests overview
    tests = [m for m in modules if modules[m]["path"].startswith("tests/") or Path(modules[m]["path"]).name.startswith("test_")]

    # GitHub readiness checklist
    checklist = {}
    for item in GITHUB_CHECKLIST:
        p = base / item
        checklist[item] = p.exists()

    return {
        "base": str(base),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "totals": {
            "py_files": len(modules),
            "classes": sum(len(modules[m]["classes"]) for m in modules),
            "functions": sum(len(modules[m]["functions"]) for m in modules),
            "globals": sum(len(modules[m]["globals"]) for m in modules),
        },
        "modules": modules,
        "import_graph": {k: sorted(v) for k, v in import_edges.items()},
        "orphans_estimate": sorted(orphan_candidates),
        "tests_detected": sorted(tests),
        "github_checklist": checklist,
    }

def write_outputs(report: Dict[str, Any], out_json: Path, out_md: Path):
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # concise markdown summary
    lines = []
    lines.append(f"# Project Audit Summary\n")
    lines.append(f"- Base: `{report['base']}`")
    lines.append(f"- Generated: `{report['generated_at']}`\n")
    t = report["totals"]
    lines.append(f"## Totals")
    lines.append(f"- Python files: **{t['py_files']}**")
    lines.append(f"- Classes: **{t['classes']}**")
    lines.append(f"- Functions: **{t['functions']}**")
    lines.append(f"- Global symbols: **{t['globals']}**\n")

    lines.append("## GitHub Readiness Checklist")
    for k, v in report["github_checklist"].items():
        emoji = "✅" if v else "❌"
        lines.append(f"- {emoji} {k}")
    lines.append("")

    if report["orphans_estimate"]:
        lines.append("## Orphan Modules (heuristic)")
        for m in report["orphans_estimate"]:
            lines.append(f"- {m}  *(path: {report['modules'][m]['path']})*")
        lines.append("")
    else:
        lines.append("## Orphan Modules (heuristic)\n- None detected\n")

    # hot spots: files with prints/breakpoints/todos
    hotspots = []
    for m, meta in report["modules"].items():
        flags = []
        if meta["uses_print"]: flags.append("print")
        if meta["uses_breakpoint"]: flags.append("breakpoint")
        if meta["todos"]: flags.append(f"TODOx{len(meta['todos'])}")
        if flags:
            hotspots.append((m, meta["path"], ", ".join(flags)))
    lines.append("## Hotspots (print/breakpoint/TODO)")
    if hotspots:
        for m, p, f in hotspots:
            lines.append(f"- {m}  *(path: {p})* → {f}")
    else:
        lines.append("- None")
    lines.append("")

    # Largest files
    largest = sorted(report["modules"].items(), key=lambda kv: kv[1]["size_bytes"], reverse=True)[:10]
    lines.append("## Largest Python Files")
    for m, meta in largest:
        lines.append(f"- {m}  → {meta['size_bytes']} bytes ({meta['loc_code']} LOC code)")
    lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Deep project scanner for audit & GitHub readiness.")
    ap.add_argument("base", nargs="?", default=".", help="Base directory (default: current dir)")
    ap.add_argument("--json", default="project_audit.json", help="Output JSON file")
    ap.add_argument("--md", default="project_audit.md", help="Output Markdown summary")
    args = ap.parse_args()

    base = Path(args.base).resolve()
    report = walk_project(base)
    write_outputs(report, Path(args.json), Path(args.md))
    print(f"✅ Wrote: {args.json} and {args.md}")

if __name__ == "__main__":
    main()
