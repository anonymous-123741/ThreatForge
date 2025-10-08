import os
import ast
from typing import List, Dict, Tuple, Set, Optional

EXCLUDE_DIRS_DEFAULT = {
    "tests", "__pycache__", "venv", "examples", "docs", "site-packages",
    "build", "dist", ".tox", ".mypy_cache", ".pytest_cache", ".venv", "notebooks", "scripts"
}

CALLBACK_CLASS_HINTS = {"callback", "handler", "observer", "hook", "event", "listener"}


FRAMEWORK_EVENT_TOKENS = {
    "LangChain": {"llm", "chain", "tool", "agent", "retriever", "chat", "embed", "run"},
    "LlamaIndex": {"llm", "query", "retriever", "node", "chunk", "ingest", "run", "event"},
    "SemanticKernel": {"function", "skill", "planner", "prompt", "invoke", "run"},
    "AutoGPT": {"agent", "task", "message", "response", "plan", "tool", "run"},
    "CrewAI": {"agent", "task", "crew", "process", "tool", "run"},
}

COMMON_PARAM_HINTS = {"run_id", "parent_run_id", "tags", "metadata", "traced", "span"}
LLAMAINDEX_PARAM_HINTS = {"event_type", "payload", "event_id", "node_id"}

def _is_py_file(file: str) -> bool:
    return file.endswith(".py")

def _looks_like_callback_class(node: ast.ClassDef) -> bool:
    name = node.name.lower()
    if any(tok in name for tok in CALLBACK_CLASS_HINTS):
        return True
    for base in node.bases:
        base_name = None
        if isinstance(base, ast.Name):
            base_name = base.id
        elif isinstance(base, ast.Attribute):
            parts = []
            cur = base
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            base_name = ".".join(reversed(parts))
        if base_name and any(tok in base_name.lower() for tok in CALLBACK_CLASS_HINTS):
            return True
    return False

def _get_arg_names(fn: ast.AST) -> Set[str]:
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return set()
    args = []
    if fn.args.posonlyargs:
        args.extend(a.arg for a in fn.args.posonlyargs)
    if fn.args.args:
        args.extend(a.arg for a in fn.args.args)
    if fn.args.kwonlyargs:
        args.extend(a.arg for a in fn.args.kwonlyargs)
    if fn.args.vararg:
        args.append(fn.args.vararg.arg)
    if fn.args.kwarg:
        args.append(fn.args.kwarg.arg)
    return set(args)

def _decorator_names(fn: ast.AST) -> Set[str]:
    names = set()
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return names
    for d in fn.decorator_list:
        if isinstance(d, ast.Name):
            names.add(d.id)
        elif isinstance(d, ast.Attribute):
            parts = []
            cur = d
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            names.add(".".join(reversed(parts)))
        elif isinstance(d, ast.Call):
            if isinstance(d.func, ast.Name):
                names.add(d.func.id)
            elif isinstance(d.func, ast.Attribute):
                parts = []
                cur = d.func
                while isinstance(cur, ast.Attribute):
                    parts.append(cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    parts.append(cur.id)
                names.add(".".join(reversed(parts)))
    return names

def _class_name_stack(stack: List[ast.AST]) -> Optional[str]:
    for n in reversed(stack):
        if isinstance(n, ast.ClassDef):
            return n.name
    return None

def _score_event_method(framework: str, fn_name: str, argnames: Set[str], in_callback_class: bool) -> Tuple[int, List[str]]:
    score = 0
    tags = []
    if not fn_name.startswith("on_"):
        return -1, tags

    score += 1
    tags.append("on_prefix")

    if in_callback_class:
        score += 2
        tags.append("callback_class")

    for tok in FRAMEWORK_EVENT_TOKENS.get(framework, set()):
        if tok in fn_name:
            score += 1
            tags.append(f"name:{tok}")

    if argnames & COMMON_PARAM_HINTS:
        score += 1
        tags.append("common_params")
    if argnames & LLAMAINDEX_PARAM_HINTS:
        score += 1
        tags.append("llamaindex_params")

    return score, tags

def find_event_triggers_in_repo(repo_path: str, framework_name: str,
                                exclude_dirs: Set[str] = None) -> List[Dict]:
    if exclude_dirs is None:
        exclude_dirs = set(EXCLUDE_DIRS_DEFAULT)

    results: List[Dict] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
        for file in files:
            if not _is_py_file(file):
                continue
            if file.startswith("test_") or file.endswith("_test.py") or file == "conftest.py":
                continue

            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    src = f.read()
                tree = ast.parse(src)
            except Exception as e:
                print(f"[WARN] Parse failed {path}: {e}")
                continue

            stack: List[ast.AST] = []

            class Visitor(ast.NodeVisitor):
                def visit_ClassDef(self, node: ast.ClassDef):
                    stack.append(node)
                    in_cb = _looks_like_callback_class(node)
                    for b in node.body:
                        if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            fn = b
                            fn_name = fn.name
                            argnames = _get_arg_names(fn)
                            score, tags = _score_event_method(framework_name, fn_name, argnames, in_cb)
                            if score >= 1:
                                results.append({
                                    "file": path,
                                    "class": node.name,
                                    "func": fn_name,
                                    "lineno": getattr(fn, "lineno", None),
                                    "score": score,
                                    "tags": tags
                                })
                    self.generic_visit(node)
                    stack.pop()

                def visit_FunctionDef(self, node: ast.FunctionDef):
                    fn_name = node.name
                    argnames = _get_arg_names(node)
                    score, tags = _score_event_method(framework_name, fn_name, argnames, in_callback_class=False)
                    if score >= 1:
                        results.append({
                            "file": path,
                            "class": None,
                            "func": fn_name,
                            "lineno": getattr(node, "lineno", None),
                            "score": score,
                            "tags": tags
                        })
                    self.generic_visit(node)

                def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                    fn_name = node.name
                    argnames = _get_arg_names(node)
                    score, tags = _score_event_method(framework_name, fn_name, argnames, in_callback_class=False)
                    if score >= 1:
                        results.append({
                            "file": path,
                            "class": None,
                            "func": fn_name,
                            "lineno": getattr(node, "lineno", None),
                            "score": score,
                            "tags": tags
                        })
                    self.generic_visit(node)

            Visitor().visit(tree)

    results.sort(key=lambda r: (-r["score"], r["file"], r["lineno"] or 0))
    return results

def print_event_summary(frameworks: Dict[str, str], topk: int = 50):

    header = f"{'Framework':<15} | {'Count':<5} | {'Top examples':<60}"
    print(header)
    print("-" * len(header))
    for fw, path in frameworks.items():
        res = find_event_triggers_in_repo(path, fw, exclude_dirs=EXCLUDE_DIRS_DEFAULT)
        top = res[:topk]
        examples = []
        for r in top[:3]:
            loc = f"{os.path.basename(r['file'])}:{r['lineno']}"
            cls = f"{r['class']+'.' if r['class'] else ''}"
            examples.append(f"{cls}{r['func']}@{loc}")
        print(f"{fw:<15} | {len(res):<5} | {('; '.join(examples)):<60}")

def save_event_details(frameworks: Dict[str, str], outfile: str = "event_triggers.tsv"):

    import csv
    rows = []
    for fw, path in frameworks.items():
        res = find_event_triggers_in_repo(path, fw, exclude_dirs=EXCLUDE_DIRS_DEFAULT)
        for r in res:
            rows.append([
                fw, r["file"], r["class"] or "", r["func"], r["lineno"] or "", r["score"], ",".join(r["tags"])
            ])
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["framework", "file", "class", "func", "lineno", "score", "tags"])
        writer.writerows(rows)
    print(f"[INFO] Saved details to {outfile}")
