import os
from dotenv import load_dotenv
from langchain.agents import Tool, create_react_agent
from langchain.agents.agent import AgentExecutor
from langchain_core.callbacks import CallbackManager
from langchain_groq import ChatGroq
from recall import OllamaFlaskCallback
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
# loader = PyPDFLoader("example.pdf")
# pages = loader.load()
# content = "\n".join([p.page_content for p in pages])

# user_input = "../../.env"

# try:
#     loader = PyPDFLoader(user_input)
#     pages = loader.load()
#     content = "\n".join([p.page_content for p in pages])
# except Exception as e:
#     content = f"[ERROR] {str(e)}"

callback = OllamaFlaskCallback("http://localhost:8002/receive", api_key=api_key)
llm = ChatGroq(
    model="deepseek-r1-distill-llama-70b",
    callbacks=[callback],
)
response = llm.predict("11111", api_key=api_key)

print(response)

