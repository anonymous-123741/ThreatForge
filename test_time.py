import time
import csv
from dotenv import load_dotenv
import os
from typing import Any, Dict, List

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_groq import ChatGroq

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
CSV_FILE = 'llm_usage.csv'

class TokenAndTimeCallback(BaseCallbackHandler):
    def __init__(self) -> None:
        self.start_time = None

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        self.start_time = time.time()
        print("Start...")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        if self.start_time is None:
            return

        end_time = time.time()
        elapsed_time = end_time - self.start_time
        print(f"Consume time {elapsed_time:.2f} 秒")

        total_tokens = 0
        if response.llm_output and 'token_usage' in response.llm_output:
            usage = response.llm_output['token_usage']
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
            print(
                f"Token consume: Prompt tokens = {prompt_tokens}, Completion tokens = {completion_tokens}, Total tokens = {total_tokens}")
        else:
            print("error")

        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            if os.path.getsize(CSV_FILE) == 0:
                writer.writerow(['time_seconds', 'total_tokens'])
            writer.writerow([round(elapsed_time, 2), total_tokens])

llm = ChatGroq(
    model="deepseek-r1-distill-llama-70b",
    callbacks=[TokenAndTimeCallback()]
)

for n in list(range(0, 1001, 30)) + [1000]:
    response = llm.invoke(f"Give me {n} words")  #