"""Generates two types of analysis for the call transcript (displayed via 2 tabs).

1. Sentiment analysis:
    - Generates gauge charts to visualise the net or speaker level percentage of positive, negative and neutral sentiments.
    - Highlights the sentiment of each interaction between the Handler and the client in the call transcript.

2. Guideline compliance:
    - Generates analytics on the guidelines followed/violated by the handler (such as greetings, PII violation, amount of time spoken, etc).
    - Generates summary of all the guidelines followed/violated by the handler.
    - Highlights the guideline followed/violated in each interaction between the Handler and the client in the call transcript.
"""

import asyncio
import re
import sys
import tomllib
from pathlib import Path

import httpx
import plotly.graph_objects as go
import streamlit as st
from functionality.text2json import text_to_json
from plot_functionality.plot_functions import (  # noqa: F401
    analyze_signs,
    get_count_message,
    get_dialog_instance,
    show_conversation_speed,
    show_sentiment,
    show_sentiment_text,
    show_time_split,
)
from loguru import logger

sys.path.append(str(Path(__file__).parent.resolve().parent.parent))
from unified_logging.config_types import LoggingConfigs
from unified_logging.logging_client import setup_network_logger_client

st.set_page_config(page_title="Call Analysis", layout="wide", initial_sidebar_state="collapsed")

st.title("Call Analysis")


# Load and configure logging
CONFIG_FILE_PATH = Path.cwd() / "Application" / "unified_logging" / "configs.toml"
logging_configs = LoggingConfigs.load_from_path(CONFIG_FILE_PATH)
setup_network_logger_client(logging_configs, logger)
logger.info("Starting Analysis.")

def load_toml_config(file_path: str = "config.toml") -> dict[str, str]:
    """Load and parse a toml configuration file."""
    with Path(file_path).open("rb") as file:
        return tomllib.load(file)

async def call_llm_function_url(chat_input: str, func_url: str) -> str | None:
    """Asynchronously call the FastAPI LLM function endpoint and return the response text."""
    async with httpx.AsyncClient(timeout=1000.0) as client:
        response = await client.get(func_url, params={"query": chat_input})
        response.raise_for_status()
        llm_response = response.json()
        return llm_response.get("response")


config = load_toml_config()
FASTAPI_LLM_FUNC_URL = config["fastapi"]["llm_function_url"]


# Radio button for analysis choice
analysis_type = st.radio(
    "Select Analysis Type:",
    ["Smart Analysis", "Complete Analysis"],
    horizontal=True,
)

## Prevent proceeding if no input file is provided
if "ip_file" not in st.session_state:
    st.warning("No file uploaded!")
    st.stop()

ip_file = st.session_state["ip_file"]
try:
    content = ip_file.read().decode("utf-8")
except AttributeError:
    content = ip_file  # already a string
except UnicodeDecodeError:
    content = ip_file.read()

## Fetch analysis for the transcript
conversation_json, attr_json,sentiment_count = text_to_json(content.getvalue())

if analysis_type == "Smart Analysis":
    st.subheader("🔍 Smart Call Analysis ")
    logger.info("Inside smart chat.")
    chat_input = st.chat_input("Plese state your question regarding the call analysis...")

    # Store chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display previous chat history
    for idx, msg in enumerate(st.session_state.chat_history):
        role, content = msg
        with st.chat_message(role):
            if isinstance(content, str):
                st.write(content)
            elif isinstance(content, list):  # multiple charts
                figures = []
                texts = []
                for item in content:
                    if isinstance(item, str):
                        texts.append(item)
                    else:
                        figures.append(item)

                # Display all text first
                for text in texts:
                    st.write(text)

                # Display all figures in columns
                if figures:
                    cols = st.columns(len(figures))
                    for i, (col, fig) in enumerate(zip(cols, figures, strict=False)):
                        with col:
                            st.plotly_chart(fig, use_container_width=True, key=f"chart_{idx}_{i}")
            else:  # single chart
                st.plotly_chart(content, use_container_width=True, key=f"chart_{idx}")

    # Process user input
    if chat_input:
        with st.chat_message("user"):
            st.write(chat_input)
            logger.info(f"Query asked:{chat_input}")

        with st.chat_message("assistant"):
            # Replace response above with api call chain.invoke({"functions": function_descriptions, "query": chat_input})
            response = asyncio.run(call_llm_function_url(chat_input, FASTAPI_LLM_FUNC_URL))
            commands = [cmd.strip() for cmd in response.split("|")]
            outputs = []

            for cmd in commands:
                # prevent hallucinations
                ALLOWED_FUNCTIONS = [
                        "show_sentiment",
                        "show_sentiment_text",
                        "show_time_split",
                        "show_conversation_speed",
                        "analyze_signs",
                        "get_dialog_instance",
                        "get_count_message",
                    ]
                if cmd.split("(")[0].strip() in ALLOWED_FUNCTIONS:
                    op = eval(cmd) # noqa: S307
                    if isinstance(op, str):
                            st.write(op)
                    elif isinstance(op, list):
                        cols = st.columns(len(op))
                        for i, (col, chart) in enumerate(zip(cols, op, strict=False)):
                            with col:
                                st.plotly_chart(chart, use_container_width=True, key=f"new_chart_{i}")
                    else:
                        st.plotly_chart(op, use_container_width=True, key=f"new_chart_{hash(cmd)}")

                    outputs.append(op)


            final_output = []
            for op in outputs:
                if isinstance(op, list):
                    final_output.extend(op)
                else:
                    final_output.append(op)

            # If single output, store directly (not in a list)
            if len(final_output) == 1:
                final_output = final_output[0]
            elif len(final_output) < 1:
                final_output = "There seems to have been an issue(possible hallucination). Please rerun"
                st.write(final_output)

        st.session_state.chat_history.append(("user", chat_input))
        st.session_state.chat_history.append(("assistant", final_output))

    st.stop()

## 2 tabs for each analysis
tab1, tab2 = st.tabs(["Sentiment Analysis","Guideline Compliance"])

with tab1:
    logger.info("Inside complete analysis.")
    # Provides insight into the sentiment during the conversation"""
    col1, col2 = st.columns(2)
    with col1:
        #  Provides gauge visualization for sentiment analysis
        #  create tab for each of the speaker values: 'Net', 'Handler', 'Client'

        tabs = st.tabs(list(sentiment_count["speakers"].keys()))

        # Iterate the tabs for Handler/Client/Overall
        for i, (speaker, sentiment) in enumerate(sentiment_count["speakers"].items()):
            with tabs[i]:  # Assign each tab to a speaker
                st.subheader(f"{speaker} Sentiment Analysis")

                # Compute sentiment percentages
                total_sp_sentiments = sentiment["positive"] + sentiment["neutral"] + sentiment["negative"]
                if total_sp_sentiments != 0:
                    sp_positive = (sentiment["positive"] / total_sp_sentiments) * 100
                    sp_neutral = (sentiment["neutral"] / total_sp_sentiments) * 100
                    sp_negative = (sentiment["negative"] / total_sp_sentiments) * 100
                else:
                    sp_positive = 0
                    sp_neutral = 0
                    sp_negative = 0

                # Create Gauge for each sentiment
                fig_sp_positive = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=sp_positive,
                    title={"text": f"{speaker} - Positive"},
                    gauge={"axis": {"range": [0, 100]}, "bar": {"color": "green"}},
                ))

                fig_sp_neutral = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=sp_neutral,
                    title={"text": f"{speaker} - Neutral"},
                    gauge={"axis": {"range": [0, 100]}, "bar": {"color": "gray"}},
                ))

                fig_sp_negative = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=sp_negative,
                    title={"text": f"{speaker} - Negative"},
                    gauge={"axis": {"range": [0, 100]}, "bar": {"color": "red"}},
                ))

                # Display each of the charts in repectiv columns
                sp_col1, sp_col2, sp_col3 = st.columns(3)
                with sp_col1:
                    st.plotly_chart(fig_sp_positive, use_container_width=True)
                with sp_col2:
                    st.plotly_chart(fig_sp_neutral, use_container_width=True)
                with sp_col3:
                    st.plotly_chart(fig_sp_negative, use_container_width=True)

    with col2:
        # Provides sentiment of each interaction between the handler and the client, and displays it in the transcript as per
        # the color theme shown in the gauge
        st.header("Call Transcript")
        for entry in conversation_json:
            col = ":grey[" ## Default for Neutral sentiment

            if entry["sentiment"] == "positive":
                col = ":green["

            elif entry["sentiment"] == "negative":
                col = ":red["

            text = entry["text"]
            for word in entry["prohibited_words"]:
                text = text.replace(word, "----")

            if entry["pil_category"]:
                text = re.sub(r"\d[\d-]*\d", "----", text)  # Replaces numbers with '----'


            if entry["speaker"] == "SPEAKER_01":
                # Handler's text
                st.markdown( f" :blue[**Handler:**] {col}**{text.strip()}**]",unsafe_allow_html=True)
            else:
                # Client's text
                st.markdown( f":orange[**Client:**] {col}**{text.strip()}**]",unsafe_allow_html=True)


with tab2:
    # Provides insight into the Guideline compliance during the conversation"""
    col1, col2 = st.columns(2)
    ## Call Transcript with guidance complaince related interactions highlighted
    with col2:
        st.header("Call Transcript")
        for entry in conversation_json:
            col = ":grey["  ## Default non Guidance related entries

            ## Handle cases where the opening and closing statement are almost identical
            ## Remove 'Closing_Statements' from 'req_phrase_cat' and update total_closures count if start_time == 0.0.
            if entry["start_time"] == 0.0 and "Closing_Statements" in entry["req_phrase_cat"]:
                entry["req_phrase_cat"].remove("Closing_Statements")
                attr_json["total_closures"] = attr_json["total_closures"] - 1

            ## Color code text based on Guideline followed or violated
            if entry["prohibited_words"]:
                col = ":red["
            elif entry["pil_category"]:
                col = ":violet["
            elif entry["req_phrase_cat"]:
                col = ":green["

            text = entry["text"]
            for word in entry["prohibited_words"]:
                text = text.replace(word, "----")

            if entry["pil_category"]:
                text = re.sub(r"\d[\d-]*\d", "----", text)  # Replaces numbers  with '----'

            ## Append a Guideline related tag to the entry to highlight the nature of the compliance/violation
            if "Disclaimers" in entry["req_phrase_cat"]:
                text += " [DISCLAIMER]"
            if "Greetings" in entry["req_phrase_cat"]:
                text += " [GREETING]"
            if "Closing_Statements" in entry["req_phrase_cat"]:
                text += " [CLOSURE]"
            if entry["prohibited_words"]:
                text += " [PROHIBITED WORDS USED]"
            if entry["pil_category"]:
                text += " [PII VIOLATION]"

            if entry["speaker"] == "SPEAKER_01":
                # Handler's final text
                st.markdown( f" :blue[**Handler:**] {col}**{text.strip()}**]",unsafe_allow_html=True)
            else:
                # Client's final text
                st.markdown( f":orange[**Client:**] {col}**{text.strip()}**]",unsafe_allow_html=True)

    with col1:
        # Provides visualizations for the Guideline compliance during the conversation"""
        tab3, tab4 = st.tabs(["Guideline Analysis","Guideline Summary"])
        with tab3:
            # Provides relevant visualizations for the Guideline followed/violated"""
            col3, col4, col5, col6, col7 = st.columns(5)
            with col3:
                st.metric(label="**:green[Total Greetings:]**", value=attr_json["total_greetings"])
            with col4:
                st.metric(label="**:green[Total Disclaimers:]**", value=attr_json["total_disclaimers"])
            with col5:
                st.metric(label="**:green[Total Closures:]**", value=attr_json["total_closures"])
            with col6:
                st.metric(label="**:violet[Total PII Violation:]**", value=attr_json["total_pil"])
            with col7:
                st.metric(label="**:red[Total Prohibited Words:]**", value=attr_json["total_prohibited_words"])

            # Charts for Handler vs client talk time and talk speed
            st.header("Speaker Statistics")
            time_labels = ["Handler", "Client"]
            time_values = [attr_json["total_agent_time"], attr_json["total_customer_time"]]
            words_labels = ["Handler", "Client"]
            words_values = [round(attr_json["total_agent_words"]/attr_json["total_agent_time"], 2), round(attr_json["total_customers_words"]/ attr_json["total_customer_time"], 2)]

            col8, col9 = st.columns(2)
            with col8:
                fig_time = go.Figure(data=[go.Pie(labels=time_labels, values=time_values,marker={"colors": ["blue", "orange"]})])
                fig_time.update_layout( title="Talk Time Split",  height=400)
                st.plotly_chart(fig_time, use_container_width=True)
            with col9:
                fig_words = go.Figure(data=[go.Bar(y=words_labels, x=words_values,  orientation="h",marker={"color": ["blue", "orange"]})] )
                fig_words.update_layout( title="Conversation Speed ", xaxis_title="Words per Second", yaxis_title="Speaker", height=400)
                st.plotly_chart(fig_words, use_container_width=True)

        with tab4:
            # Dynamically generates a summary for the guidelines followed or violated across parameters during the interaction"""
            good_signs = []
            bad_signs = []

            total_talk_time = attr_json["total_agent_time"] + attr_json["total_customer_time"]
            agent_talk_percentage = attr_json["total_agent_time"] / total_talk_time * 100 if total_talk_time > 0 else 0

            ## Ratio of time agent talked for
            agent_tk_threshold = 75
            if agent_talk_percentage > agent_tk_threshold:
                bad_signs.append(f"🔴 Handler dominated the conversation duration, with a {agent_talk_percentage:.2f}% talk time.")
            else:
                good_signs.append(f"🟢 Handler was concise with time, having used {agent_talk_percentage:.2f}% of the talk time.")
            agent_conv_threshold = 2.5
            agent_conv_speed = round(attr_json["total_agent_words"]/attr_json["total_agent_time"], 2)
            ## Ratio of words used by the Handler wrt to client
            if agent_conv_speed > agent_conv_threshold:
                bad_signs.append(f"🔴 On an average the Handler's speed was above the threshold of 2.5 WPS( WPS observed: {agent_conv_speed})")
            else:
                good_signs.append(f"🟢  On an average the Handler's speed was below the threshold of 2.5 WPS( WPS observed: {agent_conv_speed})")

            ## Atleast 1 greeting present
            if attr_json["total_greetings"] > 0:
                good_signs.append("🟢 Greetings were included.")
            else:
                bad_signs.append("🔴 Greetings were missing.")

            ## Atleast 1 disclaimer present
            if attr_json["total_disclaimers"] > 0:
                good_signs.append("🟢 Disclaimers were present.")
            else:
                bad_signs.append("🔴 Disclaimers were missing.")

            ## Atleast 1 closure present
            if attr_json["total_closures"] > 0:
                good_signs.append("🟢 Closures were handled.")
            else:
                bad_signs.append("🔴 Closures were missing.")

            ## Personally Identifiable Information violation observed or not
            if attr_json["total_pil"] > 0:
                bad_signs.append("🟣 PII leak was detected(Handler asked for account information/pin/DOB information)")
            else:
                good_signs.append("🟢 No PII leaked.")

            ## Any prohibited word used or not
            if attr_json["total_prohibited_words"] > 0:
                bad_signs.append("🔴 Handler used Profanity in text")
            else:
                good_signs.append("🟢 No profanity used")

            st.header("✅ **Good Signs**")
            if good_signs:
                for sign in good_signs:
                    st.markdown(f" **{sign}**")
            else:
                st.markdown("No good signs detected.")

            st.header("❌ **Bad Signs**")
            if bad_signs:
                for sign in bad_signs:
                    st.markdown(f" **{sign}**")
            else:
                st.markdown("No bad signs detected.")
