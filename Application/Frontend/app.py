"""
Call Analyzer - To help analyse customer service interaction and gain insights on agent performance.
"""

import asyncio
import io
import sys
import re
import tomllib
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path

import httpx
import streamlit as st
import toml
from loguru import logger

sys.path.append(str(Path(__file__).parent.resolve().parent))
from unified_logging.config_types import LoggingConfigs
from unified_logging.logging_client import setup_network_logger_client

CONFIG_FILE_PATH = Path.cwd() / "Application" / "unified_logging" / "configs.toml"
logging_configs = LoggingConfigs.load_from_path(CONFIG_FILE_PATH)
setup_network_logger_client(logging_configs, logger)
logger.info("Frontend started.")

def load_toml_config(file_path: str = "config.toml") -> dict[str, str]:
    """Load and parse a toml configuration file."""
    with Path(file_path).open("rb") as file:
        return tomllib.load(file)

async def call_process_url(call_dir: Path, process_url: str) -> httpx.Response :
    """Call the FastAPI process endpoint with the call directory path."""
    async with httpx.AsyncClient(timeout=1000.0) as client:
        return await client.get(process_url, params={"file_path": str(call_dir)})

async def call_llm_summary_url(content: str, summary_url: str) -> dict:
    """Call the FastAPI LLM summary endpoint asynchronously with the content as query."""
    async with httpx.AsyncClient(timeout=1000.0) as client:
        response = await client.get(summary_url, params={"query": content})
    return response.json()

config = load_toml_config()

if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

if "refresh" not in st.session_state:
    st.session_state.refresh = False

def refresh_page() -> None:
    """Refresh page on button click."""
    st.session_state.refresh = not st.session_state.refresh

FASTAPI_UPLOAD_URL = config["fastapi"]["upload_url"]
FASTAPI_PROCESS_URL = config["fastapi"]["process_url"]
FASTAPI_LLM_SUMM_URL = config["fastapi"]["llm_summary_url"]

# Modern Page Config
st.set_page_config(
    page_title="Call Analyzer",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "Call Analyzer - Audio and Transcript Analysis Tool"
    }
)

# Page header
header_col, refresh_col = st.columns([5, 1])
with header_col:
    st.title("📞 Customer Service Call Analyzer")
with refresh_col:
    st.button("🔄 Refresh Uploads", on_click=refresh_page, use_container_width=True)

# File Upload 
with st.container(border=True):
    st.subheader("Upload New File")
    ip_file = st.file_uploader(
        "Upload audio (.wav) for transcription or diarised call(.txt) for direct analysis",
        type=["wav", "txt"],
        label_visibility="collapsed"
    )
    
    if ip_file and not st.session_state.file_uploaded:
        file_name = ip_file.name
        file_extension = Path(file_name).suffix.lower()

        # Create directory to store the file
        current_time = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        call_dir = Path("transcripts") / f"call_{current_time}"
        call_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {call_dir}")
        # Define the storage path based on file type
        if file_extension == ".wav":
            save_path = call_dir / "audio.wav"
        elif file_extension == ".txt":
            save_path = call_dir / "diary.txt"
            with save_path.open("wb") as f:
                f.write(ip_file.getbuffer())
        else:
            st.error("❌ Unsupported file type. Please upload a valid audio (.wav) or text (.txt) file.")
            st.stop()

        with save_path.open("wb") as f:
            f.write(ip_file.getbuffer())
        st.toast(f"✅ {file_name} uploaded successfully!")
        st.session_state.file_uploaded = True

        # Audio Processing
        if file_extension == ".wav":
            with st.status("🎤 Transcribing audio...", expanded=True) as status:
                st.write("Processing your audio file")
                content = ""
                try:
                    process_response = asyncio.run(call_process_url(call_dir, FASTAPI_PROCESS_URL))
                    logger.info("processing audio")
                    with (call_dir / "diary.txt").open(encoding="utf-8") as file:
                        content = file.read()
                    if process_response.status_code == HTTPStatus.OK:
                        st.session_state["ip_file"] = content
                        st.session_state["file_type"] = 0
                    else:
                        st.error("❌ Failed to process audio file.")
                        logger.error("Failed to process audio file.")
                except httpx.HTTPError as e:
                    st.error(f"HTTP Error: {e}")
                data = asyncio.run(call_llm_summary_url(content, FASTAPI_LLM_SUMM_URL))
                toml_data = {"llm_response": data}
                summ_path = call_dir / "call_summary.toml"
                with summ_path.open("w") as f:
                    toml.dump(toml_data, f)
                    logger.info("Caching audio summary")
                status.update(label="✅ Transcription complete!", state="complete")

        # Text Processing
        elif file_extension == ".txt":
            st.toast("📝 Text file received", icon="✅")
            with st.spinner("Analyzing transcript..."):
                st.session_state["ip_file"] = ip_file
                st.session_state["file_type"] = 0
                data = asyncio.run(call_llm_summary_url(ip_file.read().decode("utf-8"), FASTAPI_LLM_SUMM_URL))
                toml_data = {"llm_response": data}
                summ_path = call_dir / "call_summary.toml"
                with summ_path.open("w") as f:
                    toml.dump(toml_data, f)

        st.balloons()

def refresh_file() -> None:
    """Refresh file cache on button click."""
    st.session_state.file_uploaded = False

def clean_string(s):
    return re.sub(r"[()\[\]{}'\"]", "", s)

if st.session_state.file_uploaded:
    st.button("Upload another file", on_click=refresh_file, use_container_width=True)

# Previous Analyses Section
st.subheader("📚 Previously analyzed calls")

transcripts_dir = Path("transcripts")
if transcripts_dir.exists() and any(transcripts_dir.iterdir()):
    tabs = st.tabs(["Most Recent"] + [""] * (len(list(transcripts_dir.iterdir())) - 1))
    
    for idx, (call_folder, tab) in enumerate(zip(sorted(transcripts_dir.iterdir(), reverse=True), tabs)):
        with tab:
            
            with st.container(border=True):
                txt_file = call_folder / "diary.txt"
                summary_file = call_folder / "call_summary.toml"
                
                if txt_file.exists():
                    cols = st.columns([3, 2, 1])
                    with cols[0]:
                        st.markdown(f"**🗓️ {call_folder.name.replace('call_', '').replace('_', ' ')}**")
                    
                    if summary_file.exists():
                        data = toml.load(summary_file)
                        response_str = data["llm_response"]["response"]
                        parts = response_str.split("'call_theme':")
                        
                        with cols[1]:
                            st.markdown(f"**Call Theme:** {parts[1].strip(" ,\n")}")
                        
                        with cols[2]:
                            if st.button("View Details", key=f"view_{call_folder.name}", use_container_width=True):
                                with Path(txt_file).open(encoding="utf-8") as f:
                                    content = f.read()
                                st.session_state["ip_file"] = io.StringIO(content)
                                st.session_state["file_type"] = 0
                                st.switch_page("pages/analytics.py")
                        
                        st.markdown(f"**Summary:** {clean_string(parts[0].replace("'summary':", "").strip(" ,\n"))}")
                        # st.divider()
else:
    st.info("No analysis history found. Upload a file to get started.", icon="ℹ️")