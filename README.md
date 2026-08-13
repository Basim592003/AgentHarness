# AgentHarness

A small agent that answers questions about a sales CSV by writing and running pandas code, with guardrails to keep it honest.

## How it works

- **`agent.py`** — the control loop. Sends the question + tool specs to the LLM, dispatches tool calls, and enforces two guardrails: `submit_answer` is rejected unless a `run_pandas_code` call has already succeeded, and unless the submitted answer contains the value that call actually computed.
- **`tools.py`** — the tools available to the model: `inspect_schema`, `run_pandas_code`, `submit_answer`. Pandas code runs in a subprocess sandbox (`PandasSandbox`) with imports, file/network access, and dunder access blocked; dataframe state persists across calls via a pickle file.
- **`llm.py`** — LLM clients: `GroqClient` (real calls to Groq).
- **`models.py`** — data classes: `Task`, `Trajectory`, `Step`, `Status`.
- **`tasks.py`** — the set of example tasks run against `data/sales.csv`, each with an expected answer.
- **`eval.py`** — scores a trajectory's final answer against the expected answer (numeric tolerance or substring match) and checks it's grounded in an actual tool result.
- **`run.py`** — entry point: runs every task in `tasks.py`, saves each trajectory to `trajectories/`, and prints a pass-rate summary.

## Running it

1. Add your Groq key to `.env`:
   ```
   GROQ_API_KEY=your-key-here
   ```
2. Run the task suite:
   ```
   python3 run.py
   ```

Each run writes a `.jsonl` trajectory log per task to `trajectories/`, plus a JSON summary with `pass_rate` and `grounded_rate` printed to stdout.

