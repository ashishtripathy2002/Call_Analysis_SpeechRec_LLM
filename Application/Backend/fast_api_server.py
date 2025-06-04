"""FAST API SERVER."""

import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_community.llms import Ollama
from loguru import logger

from Backend.speech_to_text import load_and_transcribe, save_in_txt

sys.path.append(str(Path(__file__).parent.resolve().parent))
from unified_logging.config_types import LoggingConfigs
from unified_logging.logging_client import setup_network_logger_client

CONFIG_FILE_PATH = Path.cwd() / "Application" / "unified_logging" / "configs.toml"
logging_configs = LoggingConfigs.load_from_path(CONFIG_FILE_PATH)
setup_network_logger_client(logging_configs, logger)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Preload modules."""
    # Load Ollama Model
    app.state.llm = Ollama(model="llama3")

    # Load Function Descriptions from TOML
    app.state.function_descriptions = [
            {
                "name": "show_sentiment",
                "description": "Plot sentiment analysis as graphs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sentiment_count": {
                            "type": "dict",
                            "description": "A dictionary containing sentiment related information for speakers",
                        },
                        "speaker": {
                            "type": "string",
                            "enum": ["Net", "Handler", "Client"],
                            "description": "The speaker to analyze (Net for combined, Handler for agent, Client for customer)",
                        },
                        "sentiment_type": {
                            "type": "string",
                            "enum": ["all", "positive", "neutral", "negative"],
                            "description": "Type of sentiment to display",
                        },
                    },
                    "required": ["speaker", "sentiment_type"],
                },
            },
            {
                "name": "show_sentiment_text",
                "description": "Show sentiment analysis as text summary",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sentiment_count": {
                            "type": "dict",
                            "description": "A dictionary containing sentiment related information for speakers",
                        },
                        "speaker": {
                            "type": "string",
                            "enum": ["Net", "Handler", "Client"],
                            "description": "The speaker to analyze (Net for combined, Handler for agent, Client for customer)",
                        },
                        "sentiment_type": {
                            "type": "string",
                            "enum": ["all", "positive", "neutral", "negative"],
                            "description": "Type of sentiment to display",
                        },
                    },
                    "required": ["speaker", "sentiment_type"],
                },
            },
            {
                "name": "get_count_message",
                "description": "Get count statistics for specific conversation elements like greeting, disclaimer, closure, pii violations. Used for how many or count of type questions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "attr_json": {
                            "type": "dict",
                            "description": "A dictionary containing various attribute related information like greeting, disclaimer, closure, pii",
                        },
                        "count_type": {
                            "type": "string",
                            "enum": ["greeting", "disclaimer", "closure", "pii"],
                            "description": "Type of count statistic to retrieve",
                        },
                    },
                    "required": ["attr_json","count_type"],
                },
            },
            {
                "name": "show_time_split",
                "description": "Show talk time distribution between handler and client",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "attr_json": {
                            "type": "dict",
                            "description": "A dictionary containing various attribute related information like greeting, disclaimer, closure, pii",
                        },
                        "speaker": {
                            "type": "string",
                            "enum": ["all", "handler", "client"],
                            "description": "Show comparison ('all') or specific speaker time",
                        },
                    },
                    "required": ["attr_json","speaker"],
                },
            },
            {
                "name": "show_conversation_speed",
                "description": "Show conversation speed in words per second",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "attr_json": {
                            "type": "dict",
                            "description": "A dictionary containing various attribute related information like greeting, disclaimer, closure, pii",
                        },
                        "speaker": {
                            "type": "string",
                            "enum": ["all", "handler", "client"],
                            "description": "Show comparison ('all') or specific speaker speed",
                        },
                    },
                    "required": ["attr_json","speaker"],
                },
            },
            {
                "name": "analyze_signs",
                "description": "Analyze/show good and bad signs in the conversation, only use attr_json",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "attr_json": {
                            "type": "dict",
                            "description": "A dictionary containing various attribute related information like greeting, disclaimer, closure, pii",
                        },
                        "sign_type": {
                            "type": "string",
                            "enum": ["all", "good_signs", "bad_signs"],
                            "description": "Type of signs to display",
                        },
                    },
                    "required": ["attr_json","sign_type"],
                },
            },
            {
                "name": "get_dialog_instance",
                "description": "Get specific dialog instances from the conversation like greeting, disclaimer, closure, pii violations. Used for where type questions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conversation_json": {
                            "type": "list",
                            "description": "containing call conversation level information for each dialog",
                        },
                        "dialog_type": {
                            "type": "string",
                            "enum": ["greeting", "disclaimer", "closure", "prohibited_words", "pii"],
                            "description": "Type of dialog to retrieve",
                        },
                    },
                    "required": ["dialog_type"],
                },
            },
        ]

    # Prompt for function selection
    function_prompt = ChatPromptTemplate.from_template("""
        you are an assistant that analyzes call transcripts.
        based on the user query, select only from the following functions:
        {functions}

        user query: {query}

        instructions:
        - do not invent functions — only use the ones listed above.
        - only choose function(s) from the list . do not make up new functions.
        - make sure that only the required parameters are present inside the function.
        - use only standard python *positional* syntax. no dictionaries or keyword arguments.
        - always pass the appropriate first argument ('sentiment_count', 'attr_json', or 'conversation_json') depending on the function.
        - if the query includes terms like "plot" or "graph", prioritize only those functions that include those words in their description.
        - output must be a single string. separate multiple function calls using ' | '.
        - do not include any explanation or additional text.
        - example format: show_sentiment(sentiment_count, 'Net', 'all') | show_sentiment_text(sentiment_count, 'Net', 'all') | show_time_split(attr_json, speaker)
    """)
    app.state.chain = function_prompt | app.state.llm.bind(functions=app.state.function_descriptions) | StrOutputParser()

    # Prompt for direct summarization/theme analysis
    summary_prompt = ChatPromptTemplate.from_template("""
    You are a helpful assistant that analyzes call center transcripts.
    Generate call summary(3 lines MAX) and call theme(1 line MAX) given below conversation.
    {query}
    Instructions: Do not provide any additional analysis and be strict towards the output format given below.
    Output Format: 'summary':<call summary>, 'call_theme': <theme of the given conversation>
    """)
    app.state.summary_chain = summary_prompt | app.state.llm | StrOutputParser()

    yield  # Keep resources available for API requests


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)
logger.info("FastAPI application initialized.")


@app.get("/llm_function_call")
async def analyze_function_call(query: str) -> dict[str, str]:
    """Use function selection chain to analyze the query."""
    logger.info("Function-based query received.")
    response = app.state.chain.invoke({
        "functions": app.state.function_descriptions,
        "query": query,
    })
    return {"response": str(response)}


@app.get("/llm_summary_call")
async def analyze_summary_call(query: str) -> dict[str, str]:
    """Use summary chain to directly respond to summarization or theme queries."""
    logger.info("Summary/theme query received.")
    response = app.state.summary_chain.invoke({"query": query})
    return {"response": str(response)}


@app.get("/process-audio/")
async def process_audio(file_path: str) -> FileResponse:
    """Endpoint to process an audio file."""
    trs_path = Path(file_path)
    file_path = Path(file_path) / "audio.wav"

    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return JSONResponse(status_code=404, content={"error": "File not found"})

    try:
        transcript_filename = trs_path / "diary.txt"
        transcript_path = trs_path / "diary.txt"
        if transcript_path.exists():
            logger.info(f"Returning existing transcript: {transcript_path}")
            return FileResponse(str(transcript_path), media_type="text/plain", filename=transcript_filename.name)

        # Perform transcription and diarization asynchronously
        transcript_path.touch(exist_ok=True)
        result = await asyncio.to_thread(load_and_transcribe, str(file_path))
        result_txt = await asyncio.to_thread(save_in_txt, result)

        async with aiofiles.open(transcript_path, "w") as f:
            for line in result_txt:
                await f.write(line + "\n")

        logger.info(f"Transcript generated: {transcript_path}")
        return FileResponse(str(transcript_path), media_type="text/plain", filename=transcript_filename.name)

    except ValueError as e:
        logger.exception(f"Error processing file '{file_path}': {e}")
        return JSONResponse(status_code=500, content={"error": "Error processing audio file"})


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
