# Reddit User Persona Scraper & Analyzer

This project allows you to scrape a Reddit user's public posts and comments, organize the data into manageable text chunks, and then generate a detailed persona analysis using advanced large language models (LLMs) via the Groq API.

## Features

- **Smart Data Collection**: Scrapes up to 20 posts and 20 comments from any Reddit user's public activity
- **Intelligent Organization**: Saves each post/comment as separate text chunks with full subreddit context and parent post information
- **Advanced AI Analysis**: Uses Groq's Llama-3.1-8B-Instant model for fast, accurate persona insights
- **Batch Processing**: Efficiently processes content in smart batches to avoid token limits
- **Comprehensive Reports**: Generates detailed persona analysis covering demographics, personality, interests, communication style, and motivations
- **Organized Output**: Results are saved in a clean folder structure with summary reports

## Output Structure

```
output/
└── username/
    ├── post_1.txt
    ├── post_2.txt
    ├── comment_1.txt
    ├── comment_2.txt
    ├── chunks_index.txt
    └── summary/
        ├── persona_insights.txt
        └── persona_summary.txt
```

## Requirements

- **Python 3.10** (strictly recommended)
- **Internet connection** (for Reddit scraping and Groq API)
- **Groq API account** (free tier available)

## Installation

### 1) Clone the Repository
```bash
git clone https://github.com/Siddhartha1011/reddit-persona-builder.git 
cd reddit-persona-builder
```

### 2) Create and Activate a Virtual Environment

**macOS/Linux:**
```bash
python3.10 -m venv reddit
source reddit/bin/activate
```

**Windows:**
```cmd
python -m venv reddit
.\reddit\Scripts\activate
```

### 3) Install Python Requirements
```bash
pip install -r requirements.txt
```

### 4) Set Up Environment Variables

Create a `.env` file in the project root:
```bash
GROQ_API_KEY=your_groq_api_key_here
```

Or you can enter your API key when prompted by the script.

## Usage

1. **Get a Groq API Key**:
   - Visit [console.groq.com](https://console.groq.com)
   - Sign up for a free account
   - Generate an API key

2. **Run the Script**:
   ```bash
   python reddit_user_scraper.py
   ```

3. **Enter Information**:
   - Reddit username to analyze
   - Groq API key (if not in .env file)

4. **View Results**:
   - Check the `output/username/summary/` folder for analysis results
   - `persona_insights.txt` contains batch-by-batch analysis
   - `persona_summary.txt` contains the final synthesized persona

## How It Works

1. **Data Scraping**: Fetches user's recent posts and comments from Reddit's JSON API
2. **Content Processing**: Organizes content into chunks with context (subreddit info, parent posts)
3. **Batch Analysis**: Processes content in smart batches using Groq's API
4. **Persona Synthesis**: Combines insights into a comprehensive user profile
5. **Report Generation**: Creates detailed reports with evidence citations

## Configuration

You can modify these settings in the script:

```python
MAX_POSTS = 20          # Maximum posts to scrape
MAX_COMMENTS = 20       # Maximum comments to scrape
OUTPUT_FOLDER = "output" # Output directory name
```

## Local LLM Alternative

The code can also run locally with any compatible large language model (LLM), provided your computer has sufficient resources (CPU/GPU, RAM, and disk space). You can use libraries like `llama.cpp`, `transformers`, or `text-generation-webui` to load compatible models such as Mistral, LLaMA 2/3, or Falcon in quantized formats.

### To run locally:

1. **Update the generation function**:
   ```python
   def generate_persona_from_chunks(chunk_files, llm_model_path):
       print("\n🧠 Loading local model...")
       llm = Llama(model_path=llm_model_path)
       # Add your local inference logic here
   ```

2. **Update configuration**:
   ```python
   MODEL_PATH = "path/to/your/local/model.gguf"
   ```

3. **Remove API key requirement** from the main function

While local inference avoids API costs and privacy concerns, for large-scale tasks or long prompts, cloud inference might remain the practical option for most users.

## Privacy & Ethics

- Only scrapes **public** Reddit data
- No personal information is stored beyond what users have publicly shared
- Results are saved locally on your machine
- Use responsibly and respect user privacy

## Troubleshooting

- **Rate limiting**: The script includes automatic delays to respect Reddit's API limits
- **API errors**: Check your Groq API key and account status
- **Empty results**: User might have limited public activity or account restrictions

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the project.

## License

This project is open source. Please use responsibly and in accordance with Reddit's Terms of Service and API guidelines.

