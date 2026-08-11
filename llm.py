import json


class GroqClient:
    def __init__(self, api_key, model="llama-3.3-70b-versatile"):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model

    def chat(self, messages, tools):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
        )
        message = response.choices[0].message
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in (message.tool_calls or [])
            ],
        }


class MockLLM:
    def __init__(self, script):
        self.script = script
        self.step = 0

    def chat(self, messages, tools):
        action = self.script[self.step]
        self.step += 1
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_{self.step}",
                    "type": "function",
                    "function": {"name": action["name"], "arguments": json.dumps(action["args"])},
                }
            ],
        }