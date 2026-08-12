def is_numeric(text):
    try:
        float(text)
        return True
    except (TypeError, ValueError):
        return False


def check_correctness(traj):
    task = traj.task
    if task.expected_answer is None:
        return None
    if traj.final_answer is None:
        return False

    if is_numeric(task.expected_answer) and is_numeric(traj.final_answer):
        return abs(float(traj.final_answer) - float(task.expected_answer)) <= task.tolerance

    return task.expected_answer.strip().lower() in traj.final_answer.strip().lower()


def check_groundedness(traj):
    if traj.final_answer is None:
        return None

    answer_text = traj.final_answer.strip().lower()
    for i, step in enumerate(traj.steps):
        if step.kind != "tool_call" or step.content.get("name") != "run_pandas_code":
            continue
        result_step = traj.steps[i + 1] if i + 1 < len(traj.steps) else None
        if result_step and result_step.ok and answer_text in str(result_step.content).strip().lower():
            return True
    return False


def evaluate(traj):
    return {
        "task_id": traj.task.task_id,
        "status": traj.status.value,
        "final_answer": traj.final_answer,
        "expected_answer": traj.task.expected_answer,
        "correct": check_correctness(traj),
        "grounded": check_groundedness(traj),
        "n_steps": len(traj.steps),
    }


def evaluate_suite(trajectories):
    results = [evaluate(t) for t in trajectories]
    n = len(results)
    n_correct = sum(1 for r in results if r["correct"])
    n_grounded = sum(1 for r in results if r["grounded"])
    return {
        "results": results,
        "pass_rate": n_correct / n if n else 0,
        "grounded_rate": n_grounded / n if n else 0,
    }