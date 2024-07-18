from openai import OpenAI
import json
import requests
import streamlit as st
import re

#openai_api_key = st.secrets['OPENAI_API_KEY']
endpoint_url = "https://probe.stad.gent/sparql"

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[View the source code](https://github.com/streamlit/llm-examples/blob/main/Chatbot.py)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"

with open('questions_and_queries.json', 'r', encoding='utf-8') as file:
    example_data = json.load(file)

with open('annotations_2.json', 'r', encoding='utf-8') as file:
    label_data = json.load(file)

def generate_sparql_query(user_question, label_data, examples_data):
    concepts_and_labels = "\n".join(
        f"URI of Label: {pair['uri']}\nLabel: {pair['label']}\n" for pair in label_data
    )
    example_queries = "\n".join(
        f"User Question: {pair['user_question']}\nSPARQL Query: {pair['sparql_query']}\n" for pair in examples_data
    )

    prompt = f"""
    GIVE ONLY THE QUERY AS AN ANSWER TO THE FOLLOWING PROMPT:

    The following are all the labels for the decisions in the decisions dataset and their URIs:

    {concepts_and_labels}

    Based on the user's question: {user_question}, go through all the labels then choose one label that best matches the question's theme and context.

    NEXT STEP:

    The following are examples of user questions in Dutch and their corresponding SPARQL queries:

    {example_queries}

    Based on the examples above and the URIs of the chosen labels, generate a SPARQL query for the following user question:

    User Question: {user_question}
    SPARQL Query:

    But please make sure to use the URIs of the chosen labels in the "?annotation oa:hasBody" part of the query like in the examples.
    
    If the user doesn't set a limit to the number of decisions they want to see, limit them to 3.
    
    If there is more than one URI, you can separate them with a comma.
    
    Don't add '`' as you wish.

    Then after filtering on label, add a filter for the title or description or motivering with keywords that you extract from the question.
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

def check_sparql_query(query):

    prompt = f"""
    If the query generated {query} contains looking for keywords, generate the same SPARQL query but remove the keywords filtering.
    Don't add '`' to the query as you wish.
    """
    response_2 = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a SPARQL query refiner."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0
        )

    return response_2

def run_query(query):
        headers = {
            "Accept": "application/sparql-results+json"
        }
        params = {
            "query": query
        }

        response = requests.get(endpoint_url, headers=headers, params=params)
        if response.status_code == 200:
            results = response.json()
            print(f"Results for question '{user_question}':", results)
        else:
            print(f"Failed to execute query for question '{user_question}':", response.status_code)
        
        results_content = results['results']['bindings']

        cleaned_decisions = []

        for decision in results_content:
            cleaned_decision = {}
            for key, detail in decision.items():
                # Extract the value and remove any \n or extra spaces
                cleaned_value = re.sub(r'\s+', ' ', detail['value']).strip()
                cleaned_decision[key] = cleaned_value
            cleaned_decisions.append(cleaned_decision)

        return cleaned_decisions

st.title("💬 ChatGent")
st.caption("🚀 Answering questions about decisions made by the city of Gent")
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

    user_question = prompt

    sparql_query = generate_sparql_query(user_question, label_data=label_data, examples_data=example_data)
    print(sparql_query)
    query_content = sparql_query.choices[0].message.content
    prefix_position = query_content.find("PREFIX")
    if prefix_position != -1:
        query_content = query_content[prefix_position:]

    query_content_no_newlines = query_content.replace("\n", " ")

    # print(sparql_query)

    cleaned_decisions = run_query(query_content_no_newlines)
    print(cleaned_decisions)

    if not cleaned_decisions:
        sparql_query_2 = check_sparql_query(query_content_no_newlines)
        print(sparql_query_2)
        query_content_2 = sparql_query_2.choices[0].message.content
        prefix_position = query_content.find("PREFIX")
        if prefix_position != -1:
            query_content_2 = query_content_2[prefix_position:]

        query_content_no_newlines_2 = query_content_2.replace("\n", " ")

        cleaned_decisions = run_query(query_content_no_newlines_2)
        print("again:", cleaned_decisions)

    # Print or use the cleaned_decisions as needed
    for d in cleaned_decisions:
        print(d)

    resources = []
    resources_names = []

    for d in cleaned_decisions:
        resources.append(d['derivedFrom'])
        resources_names.append(d['title'])

    prompt_2 = f"""
    The following is the question the user asked:

    {user_question}

    Based on the following data which is retrieved decisions only (ONLY THEM), generate a response that answers their question, don't hallucinate:

    Data: {cleaned_decisions}

    But before showing your answer to the user, check if it matches the user's question: {user_question}. If it relates but doesn't answer exactly mention that it might relate but isn't necessarily the answer.

    Show the {resources} to the end-user so they can refer to them. Format the links where the {resources_names} are shown as links being {resources}.

    If you don't have any answer or potential resources from the decisions which are results of the query, don't refer to any external links (including the city of Gent's website).

    Don't show empty lists in your answer. 
    Use the word "besluiten" instead of "beslissingen".

    IMPORTANT NOTE: Answer in the language the user asked in. Be sure to be friendly and explain in a way an ordinary person can understand. The language city officials use is often very different from the language citizens use (officials wind up speaking in departments and form numbers instead of needs in big organizations).
    """

    completion_2 = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant for the citizens of Gent when they ask a question on the city's website regarding the decisions made by the city. Be friendly, speak in easy to use terms. You use both the user's question and relevant decisions passed to you."},
        {"role": "user", "content": prompt_2}
    ],
    temperature=0
    )
    
    # response = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state.messages)
    msg = completion_2.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)