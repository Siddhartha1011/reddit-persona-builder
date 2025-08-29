import requests
import json
import os
import time
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -------------------------------
# CONFIGURATION
# -------------------------------

MAX_POSTS = 20
MAX_COMMENTS = 20
OUTPUT_FOLDER = "output"
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

    print(f" All chunks saved under: {user_dir}")
    print(f" Index file: {index_path}")
    return user_dir, chunk_files

# -------------------------------
# GROQ LLM GENERATION
# -------------------------------

def generate_persona_from_chunks(chunk_files, groq_api_key=None):
    print("\n Using Groq API with Llama-3.1-8B-Instant...")
    
    # Get API key from environment or parameter
    api_key = groq_api_key or os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError("Groq API key not found. Please set GROQ_API_KEY in your .env file or pass it as parameter.")
    
    # Initialize Groq client
    client = Groq(api_key=api_key)
    
    # Collect all chunk content first
    all_chunks_content = []
    print(" Reading all chunks...")
    
    for chunk_file in chunk_files:
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunk_text = f.read()
        all_chunks_content.append({
            "chunk_file": os.path.basename(chunk_file),
            "content": chunk_text
        })
    
    print(f" Processing {len(chunk_files)} chunks with smart batching...")
    
    # Try batch processing first (smaller groups)
    try:
        return generate_batch_analysis(chunk_files, client, all_chunks_content)
    except Exception as e:
        print(f"[!] Batch analysis failed: {e}")
        print("⚠️  Falling back to individual chunk analysis...")
        return generate_individual_chunk_analysis(chunk_files, client, all_chunks_content)

def generate_batch_analysis(chunk_files, client, all_chunks_content):
    """Process chunks in smaller batches to avoid token limits"""
    batch_size = 8  # Process 8 chunks at a time
    batch_insights = []
    
    # Create summary directory
    user_dir = os.path.dirname(chunk_files[0])
    summary_dir = os.path.join(user_dir, "summary")
    os.makedirs(summary_dir, exist_ok=True)
    print(f" Created summary directory: {summary_dir}")
    
    for i in range(0, len(all_chunks_content), batch_size):
        batch = all_chunks_content[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(all_chunks_content) + batch_size - 1) // batch_size
        
        print(f" Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
        
        # Combine batch content
        batch_content = "\n\n" + "="*40 + "\n\n".join([
            f"=== {chunk['chunk_file']} ===\n{chunk['content'][:1500]}" # Limit each chunk to 1500 chars
            for chunk in batch
        ])
        
        batch_prompt = f"""You are a sociologist analyzing a Reddit user's activity. Analyze this batch of posts/comments and extract persona insights.

BATCH CONTENT:
{batch_content}

Provide insights about:
- Demographics (age, location, education, etc.)
- Personality traits
- Interests and hobbies
- Communication style
- Values and motivations
- Professional indicators

Be concise but specific. Cite evidence from the posts/comments."""

        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sociologist analyzing Reddit activity. Provide concise, evidence-based persona insights."
                    },
                    {
                        "role": "user",
                        "content": batch_prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                max_tokens=1000,
                temperature=0.5,
            )
            
            batch_insight = chat_completion.choices[0].message.content
            batch_insights.append({
                "batch_num": batch_num,
                "insight": batch_insight,
                "chunks": [chunk['chunk_file'] for chunk in batch]
            })
            
            # Rate limiting
            time.sleep(2)
            
        except Exception as e:
            print(f"[!] Error processing batch {batch_num}: {e}")
            batch_insights.append({
                "batch_num": batch_num,
                "insight": f"[API Error: {str(e)}]",
                "chunks": [chunk['chunk_file'] for chunk in batch]
            })
    
    # Save batch insights in summary directory
    insights_path = os.path.join(summary_dir, "persona_insights.txt")
    with open(insights_path, "w", encoding="utf-8") as f:
        f.write("REDDIT USER PERSONA ANALYSIS (Batch Processing)\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Chunks: {len(all_chunks_content)}\n")
        f.write(f"Processed in {len(batch_insights)} batches\n")
        f.write("=" * 60 + "\n\n")
        
        for batch in batch_insights:
            f.write(f"=== BATCH {batch['batch_num']} ANALYSIS ===\n")
            f.write(f"Chunks: {', '.join(batch['chunks'])}\n\n")
            f.write(f"{batch['insight']}\n\n")
            f.write("-" * 50 + "\n\n")

    print(f" Batch persona insights saved to {insights_path}")
    
    # Generate final synthesis
    generate_synthesis_from_batches(batch_insights, client, summary_dir)
    
    return insights_path

def generate_synthesis_from_batches(batch_insights, client, summary_dir):
    """Generate final persona synthesis from batch insights"""
    print(" Synthesizing final persona profile...")
    
    # Combine batch insights (keeping it concise)
    combined_insights = "\n\n".join([
        f"BATCH {batch['batch_num']}: {batch['insight'][:800]}"  # Limit each batch insight
        for batch in batch_insights
        if not batch['insight'].startswith('[API Error')
    ])
    
    if not combined_insights:
        print("[!] No valid insights to synthesize")
        return
    
    synthesis_prompt = f"""Based on the batch analyses below, create a comprehensive Reddit user persona profile. Look for recurring patterns and synthesize the information.

BATCH INSIGHTS:
{combined_insights}

Create a final persona with these sections:
1. DEMOGRAPHIC PROFILE
2. CORE PERSONALITY 
3. PRIMARY INTERESTS
4. COMMUNICATION STYLE
5. VALUES & MOTIVATIONS
6. CONFIDENCE LEVELS

Keep it concise but comprehensive. Focus on consistent patterns across batches."""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert sociologist creating final user personas from batch analyses."
                },
                {
                    "role": "user",
                    "content": synthesis_prompt
                }
            ],
            model="llama-3.1-8b-instant",
            max_tokens=1500,
            temperature=0.3,
        )
        
        synthesis = chat_completion.choices[0].message.content
        
        # Save synthesis in summary directory
        synthesis_path = os.path.join(summary_dir, "persona_summary.txt")
        with open(synthesis_path, "w", encoding="utf-8") as f:
            f.write("FINAL REDDIT USER PERSONA SYNTHESIS\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(synthesis)
        
        print(f" Final persona synthesis saved to {synthesis_path}")
        
    except Exception as e:
        print(f"[!] Error generating synthesis: {e}")

def generate_individual_chunk_analysis(chunk_files, client, all_chunks_content):
    """Fallback: Process each chunk individually"""
    persona_chunks = []
    
    # Create summary directory
    user_dir = os.path.dirname(chunk_files[0])
    summary_dir = os.path.join(user_dir, "summary")
    os.makedirs(summary_dir, exist_ok=True)
    print(f" Created summary directory: {summary_dir}")
    
    for i, chunk_data in enumerate(all_chunks_content, 1):
        print(f"Processing chunk {i}/{len(all_chunks_content)}...")
        
        # Keep prompt concise
        prompt = f"""Analyze this Reddit activity for persona clues:

{chunk_data['content'][:1000]}  

Extract:
- Demographics
- Personality 
- Interests
- Communication style
- Motivations

Be brief but specific."""

        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                max_tokens=300,
                temperature=0.7,
            )
            output = chat_completion.choices[0].message.content
        except Exception as e:
            print(f"[!] Error processing chunk {i}: {e}")
            output = f"[API Error: {str(e)}]"
        
        persona_chunks.append({
            "chunk_file": chunk_data["chunk_file"],
            "insight": output
        })
        
        time.sleep(1)  # Rate limiting

    # Save individual insights in summary directory
    insights_path = os.path.join(summary_dir, "persona_insights.txt")
    with open(insights_path, "w", encoding="utf-8") as f:
        f.write("REDDIT USER PERSONA ANALYSIS (Individual Chunks)\n")
        f.write("=" * 60 + "\n\n")
        
        for chunk in persona_chunks:
            f.write(f"=== {chunk['chunk_file']} ===\n")
            f.write(f"{chunk['insight']}\n\n")

    print(f" Individual chunk insights saved to {insights_path}")
    return insights_path

# -------------------------------
# MAIN
# -------------------------------

if __name__ == "__main__":
    username = input("Enter Reddit username: ").strip()
    
    # Try to get API key from environment first
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        groq_api_key = input("GROQ_API_KEY not found in .env file. Enter your Groq API key: ").strip()

    print(f"\n Scraping Reddit activity for user: {username}")
    posts, comments = scrape_user_activity(username)
    
    print(f" Found {len(posts)} posts and {len(comments)} comments")
    user_dir, chunk_files = build_user_chunks(username, posts, comments)

    # Run persona generation with Groq
    insights_path = generate_persona_from_chunks(chunk_files, groq_api_key)
    print(f"\n Persona analysis complete!")
    print(f" Results saved in: {user_dir}/summary")
