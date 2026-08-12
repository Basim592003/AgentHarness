
import ast
import json
import subprocess
import sys
import textwrap
from pathlib import Path


BLOCKED_NAMES = {
    "os", "sys", "subprocess", "shutil", "socket", "requests", "urllib",
    "open", "exec", "eval", "compile", "__import__", "globals", "locals",
    "input", "breakpoint", "pty", "ctypes",
}


class ToolError(Exception):
    pass


def check_code_is_safe(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ToolError(f"code does not parse: {e}")

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ToolError("import statements are not allowed; pd and np are already available")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ToolError(f"access to dunder attribute '{node.attr}' is not allowed")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ToolError(f"use of '{node.id}' is not allowed")


class PandasSandbox:
    def __init__(self, csv_path: str, session_dir: str, timeout: float = 10.0):
        self.csv_path = csv_path
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.session_dir / "state.pkl"
        self.timeout = timeout
        self._init_state()

    def _init_state(self) -> None:
        runner = textwrap.dedent(f"""
            import pandas as pd, pickle
            df = pd.read_csv({self.csv_path!r})
            with open({str(self.state_path)!r}, "wb") as f:
                pickle.dump({{"df": df}}, f)
        """)
        subprocess.run([sys.executable, "-c", runner], timeout=self.timeout, check=True)

    def inspect_schema(self) -> str:
        runner = textwrap.dedent(f"""
            import pandas as pd, pickle, json
            with open({str(self.state_path)!r}, "rb") as f:
                state = pickle.load(f)
            df = state["df"]
            info = {{
                "columns": {{c: str(df[c].dtype) for c in df.columns}},
                "n_rows": len(df),
                "sample": df.head(3).to_dict(orient="records"),
            }}
            print(json.dumps(info, default=str))
        """)
        result = subprocess.run(
            [sys.executable, "-c", runner],
            capture_output=True, text=True, timeout=self.timeout,
        )
        if result.returncode != 0:
            raise ToolError(result.stderr.strip()[-800:])
        return result.stdout.strip()

    def run_code(self, code: str) -> str:
        check_code_is_safe(code)

        runner = textwrap.dedent(f"""
            import pandas as pd, numpy as np, pickle, json, io, contextlib

            with open({str(self.state_path)!r}, "rb") as f:
                state = pickle.load(f)
            df = state["df"]

            safe_builtins = {{
                "len": len, "range": range, "min": min, "max": max, "sum": sum,
                "sorted": sorted, "round": round, "abs": abs, "list": list,
                "dict": dict, "set": set, "str": str, "int": int, "float": float,
                "bool": bool, "enumerate": enumerate, "zip": zip, "print": print,
            }}
            g = {{"__builtins__": safe_builtins, "pd": pd, "np": np, "df": df}}

            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    exec(compile({code!r}, "<agent_code>", "exec"), g)
            except Exception as e:
                print(json.dumps({{"error": f"{{type(e).__name__}}: {{e}}"}}))
                raise SystemExit(1)

            with open({str(self.state_path)!r}, "wb") as f:
                pickle.dump({{"df": g["df"]}}, f)

            output = buf.getvalue()
            raw_result = g.get("result") if "result" in g else None
            if isinstance(raw_result, np.generic):
                raw_result = raw_result.item()
            print(json.dumps({{"stdout": output, "result": raw_result}}, default=str))
        """)

        result = subprocess.run(
            [sys.executable, "-c", runner],
            capture_output=True, text=True, timeout=self.timeout,
        )
        if result.returncode != 0:
            last_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr.strip()
            raise ToolError(last_line[-800:])
        return result.stdout.strip()


class ToolRegistry:
    def __init__(self, sandbox: PandasSandbox):
        self.sandbox = sandbox
        self.submitted_answer = None

    def specs(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "inspect_schema",
                    "description": "Return column names, dtypes, row count, and a small sample of rows from the dataset.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_pandas_code",
                    "description": (
                        "Run a pandas/numpy snippet against the dataframe df. "
                        "No imports, no file or network access. Assign the value you want "
                        "returned to a variable named result. State persists across calls."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {"code": {"type": "string", "description": "Python code using df, pd, np"}},
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "submit_answer",
                    "description": "Submit the final answer to the user's question, ending the task.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "answer": {"type": "string"},
                            "evidence": {"type": "string", "description": "The computed value(s) supporting this answer"},
                        },
                        "required": ["answer", "evidence"],
                    },
                },
            },
        ]

    def call(self, name: str, args: dict) -> tuple[bool, str]:
        try:
            if name == "inspect_schema":
                return True, self.sandbox.inspect_schema()
            elif name == "run_pandas_code":
                return True, self.sandbox.run_code(args["code"])
            elif name == "submit_answer":
                self.submitted_answer = args
                return True, json.dumps(args)
            else:
                return False, f"unknown tool '{name}'"
        except (ToolError, subprocess.TimeoutExpired) as e:
            return False, str(e)