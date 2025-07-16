
# Reddit User Persona Scraper & Analyzer
This project allows you to scrape a Reddit user’s public posts and comments, organize the data into manageable text chunks, and then generate a detailed persona analysis using advanced large language models (LLMs) via the Hugging Face Inference API.

# Features:

- Scrapes up to 50 posts and 50 comments from any Reddit user.
- Saves each post/comment as a separate text chunk, including subreddit context.
- Uses the latest LLMs (e.g., Llama 3.2-11B Vision Instruct) to extract insights about the user’s demographics, personality, interests, occupation, communication style, and motivations.
- Outputs a comprehensive persona summary, citing evidence from the user’s Reddit activity.
- Runs efficiently on any machine—no need for local GPU or large model downloads.

# Notes:

The code can also run locally on any similar large language model (LLM), provided your computer has sufficient resources (CPU/GPU, RAM, and disk space) to load and run the model smoothly. You can use libraries like llama.cpp, transformers, or text-generation-webui to load compatible models such as Mistral, LLaMA 2/3, or Falcon in quantized formats for efficient inference on consumer hardware.While local inference avoids API costs and privacy concerns,for large-scale tasks or long prompts, cloud inference might remain the only practical option for many users.

# To run the code locally:
### Update Your Code:
  ### change-

    def generate_persona_from_chunks(chunk_files, hf_token):
    
        print("\n🧠 Using Hugging Face Inference API (cloud hosted Llama-3.2-11B-Vision-Instruct)...")
    
        API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-11B-Vision-Instruct"
    
        headers = {"Authorization": f"Bearer {hf_token}"}

        def query(prompt):
      
            payload = {
      
                "inputs": prompt,
      
                "parameters": {"max_new_tokens": 512}
      
            }
      
            response = requests.post(API_URL, headers=headers, json=payload)
      
            print(response.status_code, response.text)  # For debugging
      
            try:
      
                result = response.json()
      
                # The output is a list of dicts with 'generated_text'
      
                if isinstance(result, list) and 'generated_text' in result[0]:
      
                    return result[0]['generated_text']
      
                elif isinstance(result, dict) and 'error' in result:
      
                    print(f"[!] API Error: {result['error']}")
      
                    return "[API Error]"
      
                else:
      
                    return str(result)
      
            except Exception as e:
      
                print(f"[!] Exception parsing API response: {e}")
      
                return "[API Exception]"

  ### to this-

    def generate_persona_from_chunks(chunk_files, llm_model_path):
  
        print("\n🧠 Loading Mistral model...")
    
        llm = Llama(model_path=llm_model_path)

  ### update the model path in CONFIGURATION-

    MODEL_PATH = "ENTER THE MODEL PATH HERE"
  
  ### remove this line in MAIN-
  
    hf_token = input("Enter your Hugging Face API token: ").strip()

# Requirements:
- Python 3.10 (strictly recommended)
- Internet connection (for Reddit & Hugging Face APIs)
- Hugging Face account (if using cloud inference)
- Optional: LLM model weights for local inference

# Installation:



