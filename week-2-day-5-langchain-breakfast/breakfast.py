"""Generate exactly five healthy breakfast ideas with LangChain."""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in your environment before running."
        )

    llm = ChatOpenAI(model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"))
    prompt = (
        "Give me exactly 5 healthy, gluten-free breakfast ideas for someone with a gluten allergy. "
        "Do not suggest toast, bread, wheat, barley, rye, or any other gluten-containing food. "
        "Return only the answer, with one idea per line, numbered 1 through 5, "
        "and no preamble or closing note. Keep each idea concise."
    )

    reply = llm.invoke(prompt)
    print(reply.content)


if __name__ == "__main__":
    main()
