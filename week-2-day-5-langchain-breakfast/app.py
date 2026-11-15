import os

import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

st.set_page_config(
    page_title="Healthy Gluten-Free Breakfast Ideas",
    page_icon="🍳",
    layout="centered",
)

st.title("🍳 Healthy Gluten-Free Breakfast Ideas")
st.write("Generate five healthy breakfast ideas suitable for a gluten-free diet.")

if not os.getenv("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY is missing from your .env file.")
    st.stop()


@st.cache_resource
def get_model():
    return ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        temperature=0.7,
    )


if st.button("Generate Breakfast Ideas", type="primary"):
    with st.spinner("Creating breakfast ideas..."):
        prompt = (
            "Give me exactly 5 healthy, gluten-free breakfast ideas for someone "
            "with a gluten allergy. Do not suggest toast, bread, wheat, barley, "
            "rye, or any other gluten-containing food. Eggs and omelettes are "
            "allowed. Return only the answer, with one idea per line, numbered "
            "1 through 5. Do not include a preamble or closing note."
        )

        response = get_model().invoke(prompt)
        ideas = response.content

    st.subheader("Your Breakfast Ideas")
    st.markdown(ideas)