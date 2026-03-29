import os
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util
import json

# 1. Configuration & Model Loading
# Using 'all-MiniLM-L6-v2' - an industry standard for speed and accuracy
model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_clean_text(file_path):
    if not os.path.exists(file_path): 
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    # TARGETED EXTRACTION: Only look at the actual article
    main_content = soup.find('article') or soup.find('main')
    
    if main_content:
        # Strip internal noise like script tags inside the article
        for noise in main_content(["script", "style", "aside"]):
            noise.decompose()
        text = main_content.get_text(separator=' ')
    else:
        # Fallback for CSR "Loading..." state which has no <article> tag
        text = soup.get_text(separator=' ')
        
    return " ".join(text.split())

def run_analysis():
    # 1. Load the "Source of Truth" from your JSON file
    # This is what you are comparing AGAINST.
    with open('././data/articles.json', 'r') as f:
        data = json.load(f)
        # Extract the text exactly as it appears in the article
        title = data['article']['title']
        summary = data['article']['summary']
        # Join all paragraphs from all sections
        body = " ".join([p for section in data['article']['sections'] for p in section['paragraphs']])
        original_text = f"{title} {summary} {body}"

    # 2. Extract text from the FILES your Puppeteer script generated
    # These functions will clean the HTML and return only the readable text
    # Define all 4 file paths
    path_ssr_a = './results/Profile_A_SSR.txt'
    path_ssr_b = './results/Profile_B_SSR.txt'
    path_csr_a = './results/Profile_A_CSR.txt'
    path_csr_b = './results/Profile_B_CSR.txt'
    
    # Extract text for all four
    content_ssr_a = extract_clean_text(path_ssr_a)
    content_ssr_b = extract_clean_text(path_ssr_b)
    content_csr_a = extract_clean_text(path_csr_a)
    content_csr_b = extract_clean_text(path_csr_b)
    
    # Generate embeddings (Original + 4 scraped versions)
    all_texts = [original_text, content_ssr_a, content_ssr_b, content_csr_a, content_csr_b]
    embeddings = model.encode(all_texts)
    
    # Calculate scores against original_text (index 0)
    score_ssr_a = util.cos_sim(embeddings[0], embeddings[1]).item()
    score_ssr_b = util.cos_sim(embeddings[0], embeddings[2]).item()
    score_csr_a = util.cos_sim(embeddings[0], embeddings[3]).item()
    score_csr_b = util.cos_sim(embeddings[0], embeddings[4]).item()

    # 5. Print the full table results
    print(f"{'-'*40}")
    print(f"{'Variant':<15} | {'Profile':<10} | {'SBERT Score'}")
    print(f"{'-'*40}")
    print(f"{'SSR':<15} | {'Search (A)':<10} | {score_ssr_a:.4f}")
    print(f"{'SSR':<15} | {'Agent (B)':<10} | {score_ssr_b:.4f}")
    print(f"{'CSR':<15} | {'Search (A)':<10} | {score_csr_a:.4f}")
    print(f"{'CSR':<15} | {'Agent (B)':<10} | {score_csr_b:.4f}")

if __name__ == "__main__":
    run_analysis()