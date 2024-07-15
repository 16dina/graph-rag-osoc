from openai import OpenAI
import json
import requests
import streamlit as st

# with st.sidebar:
#     openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
#     "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
#     "[View the source code](https://github.com/streamlit/llm-examples/blob/main/Chatbot.py)"
#     "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"

with open('questions_and_queries.json', 'r', encoding='utf-8') as file:
    example_data = json.load(file)

with open('annotations.json', 'r', encoding='utf-8') as file:
    label_data = json.load(file)

def generate_sparql_query(user_question, label_data, examples_data):
    concepts_and_labels = "\n".join(
        f"URI of Label: {pair['uri']}\nLabel: {pair['label']}\n" for pair in label_data
    )
    example_queries = "\n".join(
        f"User Question: {pair['user_question']}\nSPARQL Query: {pair['sparql_query']}\n" for pair in examples_data
    )

    prompt = f"""
    The following are all the labels for the decisions in the decisions dataset and their URIs:

    {concepts_and_labels}

    Based on the user's question: {user_question}, go through all the labels then choose at least 1 label that best matches the question's theme and context. 

    Get the URIs of the chosen label(s), these will be used in the next step.

    NEXT STEP:

    The following are examples of user questions in Dutch and their corresponding SPARQL queries:

    {example_queries}

    Based on the examples above and the URIs of the chosen labels, generate a SPARQL query for the following user question:

    User Question: {user_question}
    SPARQL Query:

    But please make sure to use the URIs of the chosen labels in the "?annotation oa:hasBody" part of the query like in the examples. 
    
    If there is more than one URI, you can separate them with a comma. 
    
    Make sure to not include any extra spaces or '\n' characters in the query.

    Give only the query as the answer.
    """
    response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates SPARQL queries to be run on a SPARQL endpoint containing data about decisions of the city of Gent based on user questions and labels of decisions related to their questions. Your language is Dutch."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0
        )

    return response

st.title("💬 Chatbot")
st.caption("🚀 A Streamlit chatbot powered by OpenAI")
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()

    client = OpenAI(api_key=openai_api_key)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state.messages)
    msg = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)