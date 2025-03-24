import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch  

SERPAPI_KEY = ""
MISTRAL_API_KEY = ""

def get_top_search_results(query):
    params = {
        "q": query,
        "num": 5,
        "api_key": SERPAPI_KEY
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        sources = []
        for index, res in enumerate(results.get("organic_results", [])[:5], start=1):
            source = {
                "id": str(index),
                "title": res.get("title", "Unknown Title"),
                "url": res.get("link", "Unknown URL"),
                "type": "article",
                "publisher": res.get("source", "Unknown Publisher"),
                "date": res.get("date", "Unknown Date"),
                "relevance": "95",
                "favicon": res.get("favicon", "https://defaultfavicon.com/favicon.ico")
            }
            sources.append(source)
        
        return sources 
    except Exception as e:
        print(f" SerpAPI Error: {e}")
        return []  

def scrape_website(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text_content = " ".join([para.get_text() for para in paragraphs])
        return text_content[:500000000000000000000] 
    except Exception as e:
        print(f" Error scraping {url}: {e}")
        return ""


def process_with_mistral(text):
    if not text.strip():
        return " No valid content to summarize."

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
    
    payload = {
        "model": "mistral-tiny",
        "messages": [{"role": "user", "content": f"Summarize this:\n{text}"}],
        "temperature": 0.5,
        "max_tokens": 20000
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()
    return response_data.get("choices", [{}])[0].get("message", {}).get("content", " Mistral did not return a response.")
    


def ai_scraping_agent(query):
    
    search_results = get_top_search_results(query)

    if not search_results:
        return " No search results found."

    all_text = ""
    for source in search_results:
        url = source["url"]
        print(f" Scraping: {url}")
        text = scrape_website(url)
        if text:
            all_text += text + "\n\n"

    print(" Processing with Mistral LLM...")
    summarized_text = process_with_mistral(all_text)
    
    return summarized_text
