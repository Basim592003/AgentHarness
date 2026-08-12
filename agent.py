import json

from models import Trajectory, Status
from tools import PandasSandbox, ToolRegistry

SYSTEM_PROMPT = (
    "You are a data analysis agent. You answer questions about a sales dataset "
    "using tools. Always call inspect_schema first if you have not already seen "
    "the columns. Use run_pandas_code to compute answers, never guess a number. "
    "When you have the answer, call submit_answer with the answer and the "
    "evidence you computed."
)


def run(task, llm, max_steps=8, max_consecutive_failures=3):
    sandbox = PandasSandbox(task.csv_path, session_dir=f"trajectories/{task.task_id}")
    tools = ToolRegistry(sandbox)
    traj = Trajectory(task=task)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task.question},
    ]

    for _ in range(max_steps):
        response = llm.chat(messages, tools.specs())
        messages.append(response)

        if not response.get("tool_calls"):
            traj.record("thought", response.get("content"))
            continue

        for call in response["tool_calls"]:
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])
            traj.record("tool_call", {"name": name, "args": args})

            ok, result = tools.call(name, args)
            traj.record("tool_result", result, ok=ok)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

            if ok:
                traj.consecutive_failures = 0
            else:
                traj.consecutive_failures += 1
                if traj.consecutive_failures >= max_consecutive_failures:
                    traj.status = Status.FAILED
                    return traj

            if name == "submit_answer":
                traj.final_answer = args["answer"]
                traj.status = Status.SUCCEEDED
                return traj

    traj.status = Status.MAX_STEPS
    return traj