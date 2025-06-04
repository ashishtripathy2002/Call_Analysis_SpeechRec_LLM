# __Functionality and Usage__

## __Application Features__

- __Frontend__: Presents users with multiple textual data of past calls and asks them to choose for analysis section. After uploading a file the home page reloads and the most recent update is visible at the top of the list. 

__To prevent file duplication, we have added a button called "add another file" which clears the current cache and then allows for a fresh file to be inserted.__

- __Rule Based Sentiment Analysis/Guidance Compliance__: A predefined set of hardcoded rules, stored in a YAML file for easy modification. Used RapidFuzz’s token_sort_ratio (threshold: 55) to compare input text against predefined phrases (Greetings, Disclaimers, Closing Statements) and return matched categories with counts. For compliance, regex is used to detect and flag sensitive data like account details and passwords.
- __LLM Functions__: LLM Functions is a dictionary of function descriptions used for analyzing conversations. Each function has a name, a description of its purpose, and expected parameters. Functions like show_sentiment and show_sentiment_text visualize or summarize sentiments (positive, neutral, negative) by speaker types such as Client or Handler. Others, like get_count_message and get_dialog_instance, retrieve counts or specific examples of dialog types like greetings or PII violations. show_time_split and show_conversation_speed focus on time and speed metrics between speakers. Lastly, analyze_signs identifies good or bad conversational cues.
- __Backend__: FastAPI enables asynchronous audio uploads and transcription retrieval. The frontend POSTs a .wav file, which the backend saves locally and returns its path. A GET request processes the audio with Whisper, saves the transcript, and updates the session state. Since transcription time varies by file size, an HTTP timeout of 1000s is set. Multithreading ensures a non-blocking event loop for concurrent requests, while logging tracks API activity for debugging and monitoring. FastAPI server uses LangChain to analyze call transcripts intelligently. It integrates the Ollama LLM (LLaMA3) with LangChain's ChatPromptTemplate to understand user queries and generate relevant function calls or summaries. The system defines specific functions like show_sentiment, show_time_split, and analyze_signs, and uses LangChain to select the correct one based on the query. It ensures strict formatting by guiding the LLM with detailed instructions. Two main LangChain chains are set up: one for function calling, and another for direct summarization and theme detection.

## __Pre Requisites__

- Linux OS(>= 22.04)
- Python(=3.12) 
- just (use ```sudo apt install just``` incase not installed)
- ollama (use ```curl -fsSL https://ollama.com/install.sh | sh``` incase not installed)
- llama3-8b : `just setup` handles it, incase of failure use ```ollama pull llama3 ```

## __Running the Application__

1. Clone the repository:
```git clone https://github.com/ashish142402004/llm_call_analysis.git```
2. Inside the main directory run the following commands:
    - For initial setup ```just setup```
    - To start the frontend and backend use ```just run```
    - The frontend runs on ```http://localhost:8501```
    - __Note:__ Please check if the backend is running before testing. Wait for a message like ```Server started at http://0.0.0.0:8000```


## __Known Issues:__

- additional mkdocs running in the background: use lsof -i :<port_number> to identify the process_id. Use kill -9 process_id . mkdocs may cause backend failure as it runs on same port. Please ensure it is killed before starting the project.

- As per the requirement mentioned, we have implemented the llm such that it returns the function with parameters that need to be called. However this is causing instances of hallucinations where it is creating imaginary function inspite of strict guidelines. It resolves on its own after a couple of retries.
    ![alt text](<img3.jpg>)

- `N999` ruff issues: Since we used the architecture from our speech recognition project we had used folder names of the form Frontend and Backend, which is causing this issue. We tried to change the folders to lower case form - `frontend` and `backend` but they were not getting captured in git commits, hence these issues are unresolved.

    ![alt text](<img2.jpg>)

- We are using eval() function to invoke the function returned by the llm as a string output. However this is causing  `S307` ruff issues. The alternatives available are causing the function calls to crash with the llm outputs.


- During ruff checks there was 1 failure `S105`, it is happening on account_password, mistaking the regex for a hardcoded secret. But it's just a pattern for validating strong passwords. We added `# noqa: S105` to skip the false warning safely.


<div class="grid cards" markdown>
  - [__<- App Architecture__](architecture.md)
  - [__Learning Experience ->__](experience.md)
</div>