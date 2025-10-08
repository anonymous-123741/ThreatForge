import os
import ast
from typing import List, Tuple, Dict, Set

EXCLUDE_DIRS_DEFAULT = {
    "tests", "__pycache__", "venv", "examples", "docs", "site-packages",
    "build", "dist", ".tox", ".mypy_cache", ".pytest_cache", ".venv", "notebooks", "scripts"
}

PROPERTY_DECORATORS = {
    "property", "cached_property"
}

ABSTRACT_DECORATORS = {
    "abstractmethod", "abc.abstractmethod",
    "abstractclassmethod", "abc.abstractclassmethod",
    "abstractstaticmethod", "abc.abstractstaticmethod",
    "abstractproperty", "abc.abstractproperty"  # legacy but sometimes present
}

def _decorator_names(fn: ast.AST) -> Set[str]:
    names = set()
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return names
    for d in fn.decorator_list:
        if isinstance(d, ast.Name):
            names.add(d.id)
        elif isinstance(d, ast.Attribute):
            # collect dotted path like abc.abstractmethod
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

def _is_magic(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")

def _is_public(name: str) -> bool:
    if _is_magic(name):
        return False
    return not name.startswith("_")

def _is_property(fn: ast.AST) -> bool:
    decos = _decorator_names(fn)
    if any(n.endswith("cached_property") for n in decos):
        return True
    return bool(decos & PROPERTY_DECORATORS)

def _is_abstract(fn: ast.AST) -> bool:
    decos = _decorator_names(fn)
    if decos & ABSTRACT_DECORATORS:
        return True
    # heuristic: method body raises NotImplementedError
    for node in ast.walk(fn):
        if isinstance(node, ast.Raise):
            exc = node.exc
            if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
                return True
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name) and exc.func.id == "NotImplementedError":
                return True
    return False

def _body_is_ellipsis(fn: ast.AST) -> bool:
    # protocol style stubs: def foo(self) -> None: ...
    if not fn.body:
        return False
    if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Ellipsis):
        return True
    return False

class FunctionCollector(ast.NodeVisitor):
    """
    Collect functions with context awareness:
    - parent stack to know if nested in another function
    - record class methods versus module functions
    """
    def __init__(self, *,
                 count_nested: bool = False,
                 exclude_private: bool = True,
                 exclude_magic: bool = True,
                 include_properties: bool = False,
                 only_extension_points: bool = False):
        self.stack: List[ast.AST] = []
        self.records: List[Dict] = []
        self.count_nested = count_nested
        self.exclude_private = exclude_private
        self.exclude_magic = exclude_magic
        self.include_properties = include_properties
        self.only_extension_points = only_extension_points

    def visit_ClassDef(self, node: ast.ClassDef):
        self.stack.append(node)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._record_function(node)
        # still traverse into nested defs for completeness, though they may be filtered
        self.stack.append(node)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._record_function(node)
        self.stack.append(node)
        self.generic_visit(node)
        self.stack.pop()

    def _record_function(self, node: ast.AST):
        # context
        in_class = any(isinstance(s, ast.ClassDef) for s in self.stack)
        parent_is_func = any(isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) for s in self.stack)

        # nested function filter
        if parent_is_func and not self.count_nested:
            return

        name = node.name  # type: ignore[attr-defined]

        # property filter
        if not self.include_properties and _is_property(node):
            return
        if self.exclude_magic and _is_magic(name):
            return
        if self.exclude_private and not _is_public(name):
            return

        if self.only_extension_points:
            if not (_is_abstract(node) or _body_is_ellipsis(node)):
                return

        rec = {
            "name": name,
            "kind": "method" if in_class else "function",
            "lineno": getattr(node, "lineno", None),
            "col_offset": getattr(node, "col_offset", None),
            "is_nested": parent_is_func,
            "is_property": _is_property(node),
            "is_abstract": _is_abstract(node),
        }
        self.records.append(rec)

def count_developer_methods(repo_path: str,
                            exclude_dirs: Set[str] = None,
                            *,
                            count_nested: bool = False,
                            exclude_private: bool = True,
                            exclude_magic: bool = True,
                            include_properties: bool = False,
                            only_extension_points: bool = False) -> Tuple[int, int]:

    if exclude_dirs is None:
        exclude_dirs = set(EXCLUDE_DIRS_DEFAULT)

    function_count = 0
    file_count = 0

    for root, dirs, files in os.walk(repo_path):
        # skip unwanted directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]

        for file in files:
            if not file.endswith(".py"):
                continue
            # skip common test and example file patterns
            if file.startswith("test_") or file.endswith("_test.py"):
                continue
            if file in {"conftest.py"}:
                continue

            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
                tree = ast.parse(source)
            except Exception as e:
                print(f"[WARN] Failed parsing {filepath}: {e}")
                continue

            visitor = FunctionCollector(
                count_nested=count_nested,
                exclude_private=exclude_private,
                exclude_magic=exclude_magic,
                include_properties=include_properties,
                only_extension_points=only_extension_points,
            )
            visitor.visit(tree)

            if visitor.records:
                function_count += len(visitor.records)
                file_count += 1
            else:
                file_count += 1

    return function_count, file_count

def count_functions_in_repo(repo_path: str,
                            mode: str = "public",
                            exclude_dirs: List[str] = None) -> Tuple[int, int]:
    if exclude_dirs is None:
        exclude_dirs = list(EXCLUDE_DIRS_DEFAULT)

    if mode == "public":
        return count_developer_methods(
            repo_path,
            exclude_dirs=set(exclude_dirs),
            count_nested=False,
            exclude_private=True,
            exclude_magic=True,
            include_properties=False,
            only_extension_points=False
        )
    elif mode == "all":
        return count_developer_methods(
            repo_path,
            exclude_dirs=set(exclude_dirs),
            count_nested=False,
            exclude_private=False,
            exclude_magic=True,
            include_properties=True,
            only_extension_points=False
        )
    elif mode == "extension_points":
        return count_developer_methods(
            repo_path,
            exclude_dirs=set(exclude_dirs),
            count_nested=False,
            exclude_private=True,
            exclude_magic=True,
            include_properties=False,
            only_extension_points=True
        )
    else:
        raise ValueError("Unknown mode. Use 'public', 'all', or 'extension_points'.")

if __name__ == "__main__":
    frameworks = {
        "LangChain": "langchain",
        "LlamaIndex": "llama_index",
        "SemanticKernel": "semantic-kernel/python",
        "AutoGPT": "Auto-GPT",
        "CrewAI": "crewAI",
    }

    modes = ["public", "extension_points"]
    header = f"{'Framework':<15} | {'Mode':<18} | {'Functions':<10} | {'.py Files':<10}"
    print(header)
    print("-" * len(header))
    for name, path in frameworks.items():
        for mode in modes:
            funcs, files = count_functions_in_repo(path, mode=mode)
            print(f"{name:<15} | {mode:<18} | {funcs:<10} | {files:<10}")
