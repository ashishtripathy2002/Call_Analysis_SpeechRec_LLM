![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-000000?style=for-the-badge&logo=langchain&logoColor=white)
![LLaMA 3](https://img.shields.io/badge/LLaMA_3-8E44AD?style=for-the-badge&logo=meta&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![uv](https://img.shields.io/badge/uv-6E44FF?style=for-the-badge&logo=python&logoColor=white)
![Just](https://img.shields.io/badge/Just-000000?style=for-the-badge&logo=gnubash&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)
## 🎓 Academic Affiliation

**Ashish Tripathy**  
M.Tech in Data Science  
[Indian Institute of Technology Palakkad](https://iitpkd.ac.in)  
📍 Kerala, India  


## __Pre Requisites__

- Linux OS(>= 22.04)
- Python(=3.12) 
- uv
- just (use ```sudo apt install just``` incase not installed)
- ollama (use ```curl -fsSL https://ollama.com/install.sh | sh``` incase not installed)
- llama3-8b : `just setup` handles it, incase of failure use ```ollama pull llama3 ```

## __Application Features__

- __Frontend__: Presents users with multiple textual data of past calls and asks them to choose for analysis section. After uploading a file the home page reloads and the most recent update is visible at the top of the list. 
![alt text](<docs/home_page.png>)

- __Rule Based Sentiment Analysis/Guidance Compliance__: A predefined set of hardcoded rules, stored in a YAML file for easy modification. Used RapidFuzz’s token_sort_ratio (threshold: 55) to compare input text against predefined phrases (Greetings, Disclaimers, Closing Statements) and return matched categories with counts. Results are shown in both as 
![alt text](<docs/Complete_analysis.png>)
![alt text](<docs/guideline_summ.png>)
- __LLM Functions__: LLM Functions is a dictionary of function descriptions used for analyzing conversations. Each function has a name, a description of its purpose, and expected parameters. Functions like show_sentiment and show_sentiment_text visualize or summarize sentiments (positive, neutral, negative) by speaker types such as Client or Handler. Others, like get_count_message and get_dialog_instance, retrieve counts or specific examples of dialog types like greetings or PII violations. show_time_split and show_conversation_speed focus on time and speed metrics between speakers. Lastly, analyze_signs identifies good or bad conversational cues.
![alt text](<docs/img3.jpg>)
    - **Additional Sample Questions**:  
`Where was the greeting used?`, `Show all disclaimers`, `Show all disclaimer and greeting` *(this query calls get_dialog_instance() twice once with disclaimer parameters and once with greeting parameters and renders them one after other in the chat)*

- __Backend__: 
    - FastAPI enables asynchronous audio uploads and transcription retrieval. The frontend POSTs a .wav file, which the backend saves locally and returns its path. A GET request processes the audio with Whisper, saves the transcript, and updates the session state. Since transcription time varies by file size, an HTTP timeout of 1000s is set. Multithreading ensures a non-blocking event loop for concurrent requests, while logging tracks API activity for debugging and monitoring. 
    - FastAPI server uses LangChain to analyze call transcripts intelligently. It integrates the Ollama LLM (llama3) with LangChain's ChatPromptTemplate to understand user queries and generate relevant function calls or summaries. The system defines specific functions like show_sentiment, show_time_split, and analyze_signs, and uses LangChain to select the correct one based on the query. It ensures strict formatting by guiding the LLM with detailed instructions. __Two main LangChain chains are set up: one for function calling, and another for direct summarization and theme detection.__

## __Running the Application__

1. Clone the repository

2. Inside the main directory run the following commands:
    - For initial setup ```just setup```
    - To start the frontend and backend use ```just run```
    - The frontend runs on ```http://localhost:8501```
    - __Note:__ Please check if the backend is running before testing. Wait for a message like ```Server started at http://0.0.0.0:8000```
