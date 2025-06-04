"""Rendering functionality for all llm responses."""
import plotly.graph_objects as go
import streamlit as st


def show_sentiment(sentiment_count: dict, speaker: str = "Net", sentiment_type: str = "all") -> go.Figure | list[go.Figure]:
    """Generate sentiment summary for a given speaker as chart."""
    sentiment = sentiment_count["speakers"].get(speaker, {"positive": 0, "neutral": 0, "negative": 0})
    total_sp_sentiments = sum(sentiment.values())

    if total_sp_sentiments == 0:
        sp_positive, sp_neutral, sp_negative = 0, 0, 0
    else:
        sp_positive = (sentiment["positive"] / total_sp_sentiments) * 100
        sp_neutral = (sentiment["neutral"] / total_sp_sentiments) * 100
        sp_negative = (sentiment["negative"] / total_sp_sentiments) * 100

    sentiment_charts = {
        "positive": go.Figure(go.Indicator(
            mode="gauge+number",
            value=sp_positive,
            title={"text": f"{speaker} - Positive"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": "green"}},
        )),
        "neutral": go.Figure(go.Indicator(
            mode="gauge+number",
            value=sp_neutral,
            title={"text": f"{speaker} - Neutral"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": "gray"}},
        )),
        "negative": go.Figure(go.Indicator(
            mode="gauge+number",
            value=sp_negative,
            title={"text": f"{speaker} - Negative"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": "red"}},
        )),
    }

    if sentiment_type == "all":
        return list(sentiment_charts.values())  # return all charts as a list
    if sentiment_type in sentiment_charts:
        return sentiment_charts[sentiment_type]  # return a selected chart
    st.warning("Invalid sentiment type. Choose from 'all', 'positive', 'neutral', or 'negative'.")
    return go.Figure()  # default....for wrong ip

def show_sentiment_text(sentiment_count: dict, speaker: str = "Net", sentiment_type: str = "all") -> str:
    """Generate sentiment summary for a given speaker as text."""
    if speaker not in sentiment_count["speakers"]:
        return "speaker not found in data."

    speaker_data = sentiment_count["speakers"][speaker]
    total = sum(speaker_data.values())

    if total == 0:
        return f"{speaker} has no sentiment data available."

    if sentiment_type == "all":
        result = [f"{speaker} sentiment analysis :"]
        for sentiment, count in speaker_data.items():
            percentage = (count / total) * 100
            result.append(f"  - {sentiment}: {count} ({percentage:.2f}%)")
        return "\n".join(result)

    if sentiment_type in speaker_data:
        count = speaker_data[sentiment_type]
        percentage = (count / total) * 100
        return f"{speaker} - {sentiment_type}: {count} ({percentage:.2f}%)"

    return "invalid sentiment type."

def get_count_message(attr_json: dict, count_type: str) -> str:
    """Provide count of rule compliance/ violations."""
    count_mapping = {
        "greeting": ("total_greetings", "greetings"),
        "disclaimer": ("total_disclaimers", "disclaimers"),
        "closure": ("total_closures", "closures"),
        "pii": ("total_pil", "personal information infringement"),
    }

    if count_type not in count_mapping:
        return "I did not understand what you are trying to fetch. Enter correct guideline type."

    json_key, display_text = count_mapping[count_type]
    return f"A total of {attr_json[json_key]} {display_text} found"

def get_dialog_instance(conversation_json:list, dialog_type: str) -> str:
    """Extract all instances where dialog_type that have been identified."""
    result = ["Following instances were found:"]
    dialog_config = {
        "greeting": {
            "category": "Greetings",
            "label": "greeting",
        },
        "disclaimer": {
            "category": "Disclaimers",
            "label": "disclaimer",
        },
        "closure": {
            "category": "Closing_Statements",
            "label": "closure",
        },
    }

    for entry in conversation_json:
        text_block = f"  - :green[{entry['start_time']} - {entry['end_time']}] : {entry['text']} "

        if dialog_type in dialog_config:
            category = dialog_config[dialog_type]["category"]
            label = dialog_config[dialog_type]["label"]
            if category in entry.get("req_phrase_cat", []):
                role = "Handler" if entry["speaker"] == "SPEAKER_01" else "Client"
                text_block += f":violet[[{role} {label}]]"
                result.append(text_block)

        elif dialog_type == "prohibited_words" and entry.get("prohibited_words"):
            role = "Handler" if entry["speaker"] == "SPEAKER_01" else "Client"
            text_block += f":violet[[{role} used prohibited words]]"
            result.append(text_block)

        elif dialog_type == "pii" and entry.get("pil_category"):
            role = "Handler" if entry["speaker"] == "SPEAKER_01" else "Client"
            text_block += f":violet[[{role} gave personal information]]"
            result.append(text_block)

    return "\n".join(result) if len(result) > 1 else "No such instances found in the call"

def show_time_split(attr_json: dict, speaker: str) -> go.Figure | str:
    """Return a pie chart (go.Figure) for 'all', or a string for 'handler'/'client'."""
    time_labels = ["Handler", "Client"]
    time_values = [attr_json["total_agent_time"], attr_json["total_customer_time"]]

    if speaker == "client":
        return f"client talked for {attr_json["total_customer_time"]} seconds of the total {attr_json["total_agent_time"] + attr_json["total_customer_time"]} seconds of talk time"

    if speaker == "handler":
        return f"handler talked for {attr_json["total_agent_time"]} seconds of the total {attr_json["total_agent_time"] + attr_json["total_customer_time"]} seconds of talk time"
    fig_time = go.Figure(data=[go.Pie(labels=time_labels, values=time_values, marker={"colors": ["blue", "orange"]})])
    fig_time.update_layout(title="Talk Time Split(threshold for handler: 70%)", height=400)
    return fig_time

def show_conversation_speed(attr_json: dict, speaker: str) -> go.Figure | str:
    """Return a bar chart (go.Figure) for 'all' in comparision form and a string for explicit mention of handler/client."""
    words_labels = ["Handler", "Client"]
    words_values = [
        round(attr_json["total_agent_words"] / attr_json["total_agent_time"], 2),
        round(attr_json["total_customers_words"] / attr_json["total_customer_time"], 2),
    ]

    if speaker == "all":
        fig_words = go.Figure(data=[go.Bar(y=words_labels, x=words_values, orientation="h", marker={"color": ["blue", "orange"]})])
        fig_words.update_layout(title="Conversation Speed", xaxis_title="Words per Second", yaxis_title="Speaker", height=400)
        return fig_words
    if speaker == "handler":
        return f"handler had an avg conversation speed of {words_values[0]} words/sec(threshold: 2.5 words/sec)"
    return f"client had an avg conversation speed of {words_values[1]} words/sec(threshold: 2.5 words/sec)"

def check_talk_time(attr_json: dict) -> tuple[str, str]:
    """Return talk time compliance."""
    total_time = attr_json["total_agent_time"] + attr_json["total_customer_time"]
    if total_time == 0:
        return "good", "🟢 Handler had 0 total talk time (no data)"
    agent_percent = (attr_json["total_agent_time"] / total_time) * 100
    talk_threshold = 70
    if agent_percent > talk_threshold:
        return (
            "bad",
            f"🔴 Handler dominated the conversation duration, with a {agent_percent:.2f}% talk time.",
        )
    return "good", f"🟢 Handler was concise with time, using {agent_percent:.2f}% of the talk time."

def check_conv_speed(attr_json: dict) -> tuple[str, str]:
    """Return conversation speed compliance."""
    if attr_json["total_agent_time"] == 0:
        return "bad", "🔴 Handler had 0 talk time, unable to compute conversation speed."
    conv_speed = round(attr_json["total_agent_words"] / attr_json["total_agent_time"], 2)
    speed_threshold = 2.5
    if conv_speed > speed_threshold:
        return (
            "bad",
            f"🔴 Handler's speed was above threshold (2.5 wps observed: {conv_speed:.2f})",
        )
    return (
        "good",
        f"🟢 Handler's speed was below threshold (2.5 wps observed: {conv_speed:.2f})",
    )


def check_greetings(attr_json: dict) -> tuple[str, str]:
    """Return Greeting checks."""
    if attr_json["total_greetings"] > 0:
        return "good", "🟢 Greetings were included."
    return "bad", "🔴 Greetings were missing."


def check_disclaimers(attr_json: dict) -> tuple[str, str]:
    """Return Disclaimer Checks."""
    if attr_json["total_disclaimers"] > 0:
        return "good", "🟢 Disclaimers were present."
    return "bad", "🔴 Disclaimers were missing."


def check_closures(attr_json: dict) -> tuple[str, str]:
    """Return closure checks."""
    if attr_json["total_closures"] > 0:
        return "good", "🟢 Closures were handled."
    return "bad", "🔴 Closures were missing."


def check_pii(attr_json: dict) -> tuple[str, str]:
    """Return PII violations."""
    if attr_json["total_pil"] > 0:
        return (
            "bad",
            "🔴 PII leak was detected (handler asked for account information/pin/dob information)",
        )
    return "good", "🟢 No PII leaked."


def check_profanity(attr_json: dict) -> tuple[str, str]:
    """Return profanity checks."""
    if attr_json["total_prohibited_words"] > 0:
        return "bad", "🔴 Handler used profanity in text."
    return "good", "🟢 No profanity used."


def analyze_signs(attr_json: dict, sign_type: str) -> str:
    """Return all the good and bad signs regarding the call."""
    good_signs = ["✅ Good Signs observed are:"]
    bad_signs = ["❌ Bad Signs observed are:"]

    checks = [
        check_talk_time,
        check_conv_speed,
        check_greetings,
        check_disclaimers,
        check_closures,
        check_pii,
        check_profanity,
    ]

    for check in checks:
        category, message = check(attr_json)
        formatted_message = f"\n    {message}"
        if category == "good":
            good_signs.append(formatted_message)
        else:
            bad_signs.append(formatted_message)

    if sign_type == "good_signs":
        return "\n".join(good_signs) if len(good_signs) > 1 else "no good signs detected."
    if sign_type == "bad_signs":
        return "\n".join(bad_signs) if len(bad_signs) > 1 else "no bad signs detected."

    return "\n".join(good_signs) + "\n\n" + "\n".join(bad_signs)
