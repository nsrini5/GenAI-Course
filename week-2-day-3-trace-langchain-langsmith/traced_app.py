import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import traceable

load_dotenv()

@traceable(name="week-2-day-3-langchain-app")
def run_app(user_input: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Answer clearly and concisely."),
        ("human", "{user_input}"),
    ])
    chain = prompt | ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    response = chain.invoke({"user_input": user_input})
    return response.content

if __name__ == "__main__":
    question = input("Ask a question: ")
    print("\nAnswer:")
    print(run_app(question))
