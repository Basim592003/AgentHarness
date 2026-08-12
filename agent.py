import json

from models import Trajectory, Status
from tools import PandasSandbox, ToolRegistry

SYSTEM_PROMPT = (
    "You are a data analysis agent. You answer questions about a sales dataset "
    "using tools. Always call inspect_schema first if you have not already seen "
    "the columns, and use the exact column names it reports (never guess column "
    "names). Date columns are stored as strings. To filter or group by "
    "year/month, convert the whole column at once and use the .dt accessor "
    "on it directly, e.g. pd.to_datetime(df['order_date']).dt.year == 2023 - "
    "never call pd.to_datetime inside .apply on individual values, since .dt "
    "only works on a Series, not a scalar Timestamp. "
    "Use run_pandas_code to compute answers, never guess a number. If it returns "
    "an error, fix the code and try again rather than submitting an answer. "
    "Once run_pandas_code succeeds, its JSON output has a 'result' field holding "
    "the computed value - copy that exact value into submit_answer's answer "
    "field."
)


def run(task, llm, max_steps=8, max_consecutive_failures=3):
    sandbox = PandasSandbox(task.csv_path, session_dir=f"trajectories/{task.task_id}")
    tools = ToolRegistry(sandbox)
    traj = Trajectory(task=task)
    has_computed_result = False
    last_result = None

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task.question},
    ]

    for _ in range(max_steps):
        try:
            response = llm.chat(messages, tools.specs())
        except Exception as e:
            traj.record("llm_error", str(e), ok=False)
            traj.consecutive_failures += 1
            if traj.consecutive_failures >= max_consecutive_failures:
                traj.status = Status.FAILED
                return traj
            continue

        messages.append(response)

        if not response.get("tool_calls"):
            traj.record("thought", response.get("content"))
            continue

        for call in response["tool_calls"]:
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])
            traj.record("tool_call", {"name": name, "args": args})

            if name == "submit_answer" and not has_computed_result:
                ok, result = False, (
                    "submit_answer rejected: you have not yet gotten a successful "
                    "result from run_pandas_code. Call run_pandas_code to compute "
                    "the answer before submitting."
                )
            elif (
                name == "submit_answer"
                and last_result is not None
                and str(last_result).strip().lower() not in str(args.get("answer", "")).strip().lower()
            ):
                ok, result = False, (
                    f"submit_answer rejected: your last successful run_pandas_code call "
                    f"computed {last_result!r}, but your answer does not contain that "
                    f"value. Use the actual computed value as the answer."
                )
            else:
                ok, result = tools.call(name, args)

            traj.record("tool_result", result, ok=ok)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

            if name == "run_pandas_code" and ok:
                has_computed_result = True
                try:
                    last_result = json.loads(result).get("result")
                except (json.JSONDecodeError, AttributeError):
                    pass

            if ok:
                traj.consecutive_failures = 0
            else:
                traj.consecutive_failures += 1
                if traj.consecutive_failures >= max_consecutive_failures:
                    traj.status = Status.FAILED
                    return traj

            if name == "submit_answer" and ok:
                traj.final_answer = args["answer"]
                traj.status = Status.SUCCEEDED
                return traj

    traj.status = Status.MAX_STEPS
    return traj