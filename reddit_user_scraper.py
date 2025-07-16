import requests
import json
import os
import time
from llama_cpp import Llama

# -------------------------------
# CONFIGURATION
# -------------------------------

MAX_POSTS = 50
MAX_COMMENTS = 50
OUTPUT_FOLDER = "output"
MODEL_PATH = "Enter the model path here"
USER_AGENT = "RedditPersonaBot/1.0"

# Make sure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------------------
# REDDIT SCRAPING
# -------------------------------

def reddit_get_json(url):
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[!] Error fetching {url} (status code {resp.status_code})")
            return None
    except Exception as e:
        print(f"[!] Request error: {e}")
        return None

def scrape_user_activity(username):
    base_url = f"https://www.reddit.com/user/{username}/.json"
    after = None
    posts, comments = [], []

    while True:
        url = base_url
        if after:
            url += f"?after={after}"

        data = reddit_get_json(url)
        if not data:
            break

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        for item in children:
            kind = item.get("kind")
            d = item.get("data", {})

            if kind == "t3":
                posts.append({
                    "title": d.get("title", ""),
                    "body": d.get("selftext", ""),
                    "subreddit": d.get("subreddit", ""),
                    "permalink": "https://www.reddit.com" + d.get("permalink", "")
                })
            elif kind == "t1":
                comments.append({
                    "body": d.get("body", ""),
                    "subreddit": d.get("subreddit", ""),
                    "permalink": "https://www.reddit.com" + d.get("permalink", ""),
                    "link_id": d.get("link_id", "")
                })

        after = data.get("data", {}).get("after")
        if not after:
            break

        if len(posts) >= MAX_POSTS and len(comments) >= MAX_COMMENTS:
            break

        time.sleep(1)

    return posts[:MAX_POSTS], comments[:MAX_COMMENTS]

def fetch_parent_post(post_id):
    url = f"https://www.reddit.com/comments/{post_id}/.json"
    data = reddit_get_json(url)
    if not data or len(data) < 1:
        return None
    post_data = data[0]["data"]["children"][0]["data"]
    return {
        "title": post_data.get("title", ""),
        "body": post_data.get("selftext", ""),
        "subreddit": post_data.get("subreddit", ""),
        "permalink": "https://www.reddit.com" + post_data.get("permalink", "")
    }

def fetch_subreddit_description(subreddit_name):
    url = f"https://www.reddit.com/r/{subreddit_name}/about.json"
    data = reddit_get_json(url)
    return data.get("data", {}).get("public_description", "") if data else ""

# -------------------------------
# CHUNKING LOGIC
# -------------------------------

def build_user_chunks(username, posts, comments):
    subreddit_descriptions = {}
    chunk_files = []
    user_dir = os.path.join(OUTPUT_FOLDER, username)
    os.makedirs(user_dir, exist_ok=True)

    index_lines = []

    # Process posts
    for i, post in enumerate(posts, start=1):
        subreddit = post["subreddit"]
        if subreddit not in subreddit_descriptions:
            desc = fetch_subreddit_description(subreddit)
            subreddit_descriptions[subreddit] = desc
        else:
            desc = subreddit_descriptions[subreddit]

        chunk_text = f"""[POST #{i}]
Title: {post['title']}
Body: {post['body']}
Subreddit: {subreddit}
Subreddit Description: {desc}
URL: {post['permalink']}
"""

        chunk_filename = f"post_{i}.txt"
        chunk_path = os.path.join(user_dir, chunk_filename)
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(chunk_text)

        chunk_files.append(chunk_path)
        index_lines.append(f"[POST #{i}] → {chunk_filename}")

    # Process comments
    for i, comment in enumerate(comments, start=1):
        subreddit = comment["subreddit"]
        if subreddit not in subreddit_descriptions:
            desc = fetch_subreddit_description(subreddit)
            subreddit_descriptions[subreddit] = desc
        else:
            desc = subreddit_descriptions[subreddit]

        chunk_text = f"""[COMMENT #{i}]
Comment: {comment['body']}
Subreddit: {subreddit}
Subreddit Description: {desc}
URL: {comment['permalink']}
"""

        if comment.get("link_id", "").startswith("t3_"):
            post_id = comment["link_id"][3:]
            parent_post = fetch_parent_post(post_id)
            if parent_post:
                chunk_text += f"""Parent Post Title: {parent_post['title']}
Parent Post Body: {parent_post['body']}
Parent Post Subreddit: {parent_post['subreddit']}
Parent Post URL: {parent_post['permalink']}
"""

        chunk_filename = f"comment_{i}.txt"
        chunk_path = os.path.join(user_dir, chunk_filename)
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(chunk_text)

        chunk_files.append(chunk_path)
        index_lines.append(f"[COMMENT #{i}] → {chunk_filename}")

    # Save chunk index
    index_path = os.path.join(user_dir, "chunks_index.txt")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    print(f"✅ All chunks saved under: {user_dir}")
    print(f"✅ Index file: {index_path}")
    return user_dir, chunk_files

# -------------------------------
# LLM GENERATION
# -------------------------------

def generate_persona_from_chunks(chunk_files, hf_token):
    # Using Meta Llama 3.2-11B Vision Instruct model. You may need to accept terms or request access on Hugging Face.
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

    persona_chunks = []
    for chunk_file in chunk_files:
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunk_text = f.read()

        prompt = f"""You are a sociologist. Given the following Reddit activity chunk, extract any clues about the user's demographics, personality, interests, occupation, communication style, or motivations. Cite specific evidence from the chunk.\n\nReddit Activity Chunk:\n{chunk_text}\n\nInsights:"""

        output = query(prompt)
        # Remove the prompt from the output if present
        insight = output.split("Insights:")[-1].strip() if "Insights:" in output else output.strip()
        persona_chunks.append({
            "chunk_file": chunk_file,
            "insight": insight
        })

    # Save all insights
    insights_path = os.path.join(os.path.dirname(chunk_files[0]), "persona_insights.txt")
    with open(insights_path, "w", encoding="utf-8") as f:
        for chunk in persona_chunks:
            f.write(f"=== {chunk['chunk_file']} ===\n{chunk['insight']}\n\n")

    print(f"✅ Persona insights saved to {insights_path}")
    return insights_path

# -------------------------------
# MAIN
# -------------------------------

if __name__ == "__main__":
    username = input("Enter Reddit username: ").strip()
    hf_token = input("Enter your Hugging Face API token: ").strip()

    posts, comments = scrape_user_activity(username)
    user_dir, chunk_files = build_user_chunks(username, posts, comments)

    # Run persona generation
    insights_path = generate_persona_from_chunks(chunk_files, hf_token)
    print(f"\n🎯 Persona summary is ready: {insights_path}")
