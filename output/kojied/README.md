# Reddit Persona Analysis – u/kojied

The directory `output/kojied` contains all the data and intermediate files generated during the scraping and analysis of Reddit activity for the user **kojied**.  

## Structure

### 📂 chunks_index.txt
- An index file listing all the **text chunks** created from the user’s Reddit posts and comments.  
- Each chunk represents a segment of text that was later passed into the analysis pipeline.  
- This file serves as a reference map for locating and processing content efficiently.

### 📂 Chunks
- Subdirectory (or stored inline) containing all the **individual text chunks** derived from 20 posts and 20 comments.  
- Each chunk is a manageable text unit for batch analysis.  
- Used as input for the LLM to avoid token size limitations.

### 📂 summary
- Final analysis results folder.  
- Contains:
  - **persona_insights.txt** → Batch-level insights (tone, themes, behavioral signals).  
  - **persona_summary.txt** → Final synthesized persona profile (personality traits, interests, values, patterns).  

## Workflow Recap
1. **Scraping:** 20 posts + 20 comments from Reddit user **kojied**.  
2. **Chunking:** Content split into smaller, token-friendly text files.  
3. **Indexing:** All chunks referenced in `chunks_index.txt`.  
4. **Batch Analysis:** Smart batching applied, insights saved.  
5. **Final Summary:** Cohesive persona profile written to `summary/`.  

---

📂 `output/kojied` = the **full dataset + results** for persona analysis, including **raw chunks, indexing, and the final summary reports**.
