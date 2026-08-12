import os
import json
from dotenv import load_dotenv
load_dotenv()
from tasks import TASKS
from llm import GroqClient
import agent
import eval as evaluator

api_key = os.environ.get("GROQ_API_KEY")
llm = GroqClient(api_key=api_key)

trajectories = []
for task in TASKS:
    print(f"running {task.task_id}: {task.question}")
    try:
        traj = agent.run(task, llm)
    except Exception as e:
        print(f"task {task.task_id} crashed: {e}")
        print("---")
        continue
    traj.save(f"trajectories/{task.task_id}.jsonl")
    trajectories.append(traj)
    print(traj.summary())
    print("---")

summary = evaluator.evaluate_suite(trajectories)
print(json.dumps(summary, indent=2))