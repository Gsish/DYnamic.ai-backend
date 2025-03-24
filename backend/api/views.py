from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
import datetime
import re
import os
import json
from django.conf import settings
from .generator import (
    fetch_company_data,
    create_prompt_template,
    generate_long_report,
    generate_graph,
    generate_seaborn_graph,
    generate_pdf,
    generate_docx,
)
import yfinance as yf
import requests
from .ai import get_top_search_results, ai_scraping_agent
from functools import lru_cache
from datetime import datetime, timedelta

# Direct API key configuration
MISTRAL_API_KEY = "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"
MISTRAL_API_URL = "https://openrouter.ai/api/v1"

# Cache AI responses for future use
_response_cache = {}

def cache_ai_response(response):
    """Store AI response in memory cache with timestamp."""
    _response_cache["last_response"] = {
        "content": response,
        "timestamp": datetime.now()
    }
    
def get_cached_response():
    """Retrieve the most recent AI response if available."""
    cache_entry = _response_cache.get("last_response")
    if cache_entry:
        return cache_entry["content"]
    return ""

@api_view(["POST"])
def ai_query_view(request):
    """Process AI queries with search results and responses."""
    try:
        query = request.data.get("query", "").strip()

        if not query:
            return Response({"error": "Please enter a query."}, status=400)

            
        ai_response = ai_scraping_agent(query)  
        search_results = get_top_search_results(query)
        
        
        # Store response in cache for later use
        cache_ai_response(ai_response)

        response_data = {
            "response": ai_response,
            "confidence": 0.85,
            "sources": search_results
        }
        return JsonResponse(response_data)
    except Exception as e:
        import logging
        logging.error(f"Error in AI query view: {str(e)}", exc_info=True)
        return Response(
            {"error": "Something went wrong. Please try again later."}, 
            status=500
        )

NEWS_API_KEY = "0a1f54e3ee7749b68339dc8883cd42ff"  
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"

@api_view(["GET"])
def news_articles(request):
    """Fetch news articles from NewsAPI, filterable by category."""
    category = request.GET.get("category", "")

    params = {
        "apiKey": NEWS_API_KEY,
        "country": "us",  
    }

    if category:
        params["category"] = category.lower()

    response = requests.get(NEWS_API_URL, params=params)

    if response.status_code == 200:
        data = response.json().get("articles", [])
        
        formatted_articles = [
            {
                "id": str(1),  
                "title": str(article.get("title", "No title")),
                "source":str(article.get("source", {}).get("name", "Unknown")),
                "summary": str(article.get("description", "No summary available")),
                "url": str(article.get("url", "#")),
                "publishedAt": str(article.get("publishedAt", "Unknown date")),
                "category": str(category if category else "general"),
                "imageUrl": str(article.get("urlToImage", None)),
            }
            for article in data
        ]

        return Response(formatted_articles)
    
    return Response({"error": "Failed to fetch news articles"}, status=500)

def get_mock_articles():
    """Return mock articles for demo purposes."""
    return [
        {
            "id": "1",
            "title": "AI Breakthrough in 2025",
            "source": "Tech Times",
            "summary": "A major breakthrough in AI has been achieved, changing the landscape of technology.",
            "url": "https://www.techtimes.com/ai-breakthrough-2025",
            "publishedAt": datetime.now().isoformat(),
            "category": "Technology",
            "imageUrl": "https://www.techtimes.com/images/ai.jpg"
        }
        
    ]

@lru_cache(maxsize=100)
def extract_company_names(text):
    """
    Extract company names from text using Mistral API with caching for performance.
    """
    if not text:
        
        return ["Apple", "Microsoft", "Google"]
        
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "text",
            "content": text
        }
    }
    
    try:
        response = requests.post(MISTRAL_API_URL, json=payload, headers=headers)
        response.raise_for_status()  
        
        result = response.json()
        company_names = [entity['text'] for entity in result.get('entities', []) 
                       if entity['type'] == 'ORG']
        
        
        if not company_names:
            return ["Apple", "Microsoft", "Google","tesla","amazon","facebook","meta","nvidia","amd","intel","ibm","oracle","salesforce","adobe"]
            
        return company_names
    except requests.exceptions.RequestException as e:
        import logging
        logging.error(f"Error in Mistral API call: {str(e)}")
        return ["Apple", "Microsoft", "Google","amazon","facebook","meta","nvidia","amd","intel","ibm","oracle","salesforce","adobe"]  

def get_ticker_symbols(company_names):
    """
    Fetch ticker symbols for company names using yfinance.
    """
    if not company_names:
        return {"Apple": "AAPL", "Microsoft": "MSFT", "Google": "GOOGL", "Amazon": "AMZN", "Tesla": "TSLA", "Facebook": "META", "Meta": "META", "Netflix": "NFLX", "Nvidia": "NVDA", "AMD": "AMD", "Intel": "INTC", "IBM": "IBM", "Oracle": "ORCL", "Salesforce": "CRM", "Adobe": "ADBE"}
        
    
    common_tickers = {
        "Apple": "AAPL",
        "Microsoft": "MSFT", 
        "Google": "GOOGL",
        "Amazon": "AMZN",
        "Tesla": "TSLA",
        "Facebook": "META",
        "Meta": "META",
        "Netflix": "NFLX",
        "Nvidia": "NVDA",
        "AMD": "AMD",
        "Intel": "INTC",
        "IBM": "IBM",
        "Oracle": "ORCL",
        "Salesforce": "CRM",
        "Adobe": "ADBE"
    }
        
    ticker_symbols = {}
    for name in company_names:
        
        if name in common_tickers:
            ticker_symbols[name] = common_tickers[name]
            continue
            
        try:
            ticker = yf.Ticker(name)
            info = ticker.info
            if 'symbol' in info:
                ticker_symbols[name] = info['symbol']
            else:
                ticker_symbols[name] = name  
        except Exception as e:
            import logging
            logging.warning(f"Error fetching ticker symbol for {name}: {str(e)}")
            ticker_symbols[name] = name  
    
    
    if not ticker_symbols:
        return {"Apple": "AAPL", "Microsoft": "MSFT", "Google": "GOOGL", "Amazon": "AMZN", "Tesla": "TSLA", "Facebook": "META", "Netflix": "NFLX", "Nvidia": "NVDA", "AMD": "AMD", "Intel": "INTC", "IBM": "IBM", "Oracle": "ORCL", "Salesforce": "CRM", "Adobe": "ADBE"}
        
    return ticker_symbols

def fetch_stock_data(company_names, time_range="1d"):
    """
    Fetch stock data for company names using yfinance.
    """
    if not company_names:
        
        return generate_mock_stock_data()
        
    
    if isinstance(company_names, tuple):
        company_names = list(company_names)
        
    ticker_symbols = get_ticker_symbols(company_names)
    stock_data = []

    for name, symbol in ticker_symbols.items():
        if not symbol:
            continue
            
        try:
            
            ticker = yf.Ticker(symbol)
            stock_info = ticker.history(period=time_range)

            
            if stock_info.empty:
                mock_data = generate_mock_data_for_symbol(symbol, name, time_range)
                stock_data.append(mock_data)
                continue

            
            dates = [str(date.date()) for date in stock_info.index]
            prices = [round(float(price), 2) for price in stock_info["Close"].tolist()]
            
            
            if len(prices) >= 2:
                latest_close = prices[-1]
                prev_close = prices[-2]
            else:
                
                latest_close = prices[0]
                prev_close = latest_close * 0.99 
                
            change = latest_close - prev_close
            change_percent = (change / prev_close) * 100 if prev_close != 0 else 0

            stock_data.append({
                "symbol": symbol,
                "name": name,
                "prices": prices,
                "dates": dates,
                "change": round(float(change), 2),
                "changePercent": round(float(change_percent), 2),
            })
        except Exception as e:
            import logging
            logging.error(f"Error fetching stock data for {symbol}: {str(e)}")
            
            mock_data = generate_mock_data_for_symbol(symbol, name, time_range)
            stock_data.append(mock_data)

    
    if not stock_data:
        return generate_mock_stock_data()
        
    return stock_data

def generate_mock_data_for_symbol(symbol, name, time_range):
    """Generate realistic mock data for a symbol when real data isn't available."""
    import random
    
    
    days_mapping = {
        "1d": 1,
        "5d": 5,
        "1w": 7,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "ytd": datetime.now().timetuple().tm_yday,  
        "max": 1825  
    }
    
    num_days = days_mapping.get(time_range, 30)  
    
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days)]
    dates.reverse()  
    
    
    base_price = random.uniform(50, 200)  
    volatility = random.uniform(0.005, 0.02)  
    
    prices = []
    current_price = base_price
    
    for _ in range(num_days):
        current_price *= (1 + random.uniform(-volatility, volatility))
        prices.append(round(current_price, 2))
    
    
    if len(prices) >= 2:
        latest_price = prices[-1]
        prev_price = prices[-2]
        change = latest_price - prev_price
        change_percent = (change / prev_price) * 100 if prev_price != 0 else 0
    else:
        latest_price = prices[0]
        change = 0
        change_percent = 0
    
    return {
        "symbol": symbol,
        "name": name,
        "prices": prices,
        "dates": dates,
        "change": round(change, 2),
        "changePercent": round(change_percent, 2),
    }

def generate_mock_stock_data():
    """Generate mock stock data for default companies."""
    default_companies = [
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"},
        {"symbol": "GOOGL", "name": "Google"},
        {"symbol": "AMZN", "name": "Amazon"},
        {"symbol": "TSLA", "name": "Tesla"},
        {"symbol": "META", "name": "Meta"},
        {"symbol": "NFLX", "name": "Netflix"},
        {"symbol": "NVDA", "name": "Nvidia"},
        {"symbol": "AMD", "name": "AMD"},
        {"symbol": "INTC", "name": "Intel"},
        {"symbol": "IBM", "name": "IBM"},
        {"symbol": "ORCL", "name": "Oracle"},
        {"symbol": "CRM", "name": "Salesforce"},
        {"symbol": "ADBE", "name": "Adobe"}
    ]
    
    stock_data = []
    for company in default_companies:
        mock_data = generate_mock_data_for_symbol(
            company["symbol"], 
            company["name"], 
            "1mo"
        )
        stock_data.append(mock_data)
        
    return stock_data

def generate_response(company_names, time_range="1d"):
    """
    Generate JSON response with stock data.
    """
    stock_data = fetch_stock_data(company_names, time_range)
    response = {
        "data": stock_data,
        "lastUpdated": datetime.now().isoformat()
    }
    return response

@api_view(["GET"])
def search_news(request):
    """Search news articles based on query."""
    query = request.GET.get("query", "")
    articles = get_mock_articles()

    if query:
        filtered_articles = [
            article for article in articles 
            if query.lower() in article["title"].lower() or 
               query.lower() in article["summary"].lower()
        ]
    else:
        filtered_articles = articles

    return Response(filtered_articles)

@api_view(["GET"])
def search_stocks(request):
    """Search stocks based on company names in last AI response."""
    try:
        query = request.GET.get("query", "").strip().lower()
        
        
        ai_response = get_cached_response()
        company_names = extract_company_names(ai_response)
        
        if not company_names and query:
            
            company_names = [query]
            
        
        if not company_names:
            company_names = ["Apple", "Microsoft", "Google", "Amazon", "Tesla", "Facebook", "Meta", "Nvidia", "AMD", "Intel", "IBM", "Oracle", "Salesforce", "Adobe"]
        
        response = generate_response(company_names, time_range="1d")
        return JsonResponse(response, safe=False)
    except Exception as e:
        import logging
        logging.error(f"Error in search_stocks: {str(e)}", exc_info=True)
        
        mock_response = generate_response(["Apple", "Microsoft", "Google","Amazon", "Tesla", "Facebook", "Meta", "Nvidia", "AMD", "Intel", "IBM", "Oracle", "Salesforce", "Adobe"], "1d")
        return JsonResponse(mock_response, safe=False)

@api_view(["GET"])
def get_stock_data(request):
    """Get stock data for a specific time range."""
    try:
        time_range = request.GET.get("timeRange", "")
        valid_ranges = ["1d", "5d", "1w", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
        
        if time_range not in valid_ranges:
            time_range = "1w"  
        
        
        ai_response = get_cached_response()
        company_names = extract_company_names(ai_response)
        
        
        if not company_names:
            company_names = ["Apple", "Microsoft", "Google", "Amazon", "Tesla", "Facebook", "Meta", "Nvidia", "AMD", "Intel", "IBM", "Oracle", "Salesforce", "Adobe"]
        
        response = generate_response(company_names, time_range=time_range)
        return JsonResponse(response, safe=False)
    except Exception as e:
        import logging
        logging.error(f"Error in get_stock_data: {str(e)}", exc_info=True)
        
        mock_response = generate_response(["Apple", "Microsoft", "Google","Amazon", "Tesla", "Facebook", "Meta", "Nvidia", "AMD", "Intel", "IBM", "Oracle", "Salesforce", "Adobe"], time_range)
        return JsonResponse(mock_response, safe=False)

@api_view(["POST"])
def generate_report(request):
    """Generate detailed financial report based on ticker symbol."""
    try:
        query = request.data.get("ticker", "").strip()
        if not query:
            return Response({"error": "No ticker provided"}, status=400)

        ticker_symbol = query
        company_data = fetch_company_data(ticker_symbol)

        if not company_data:
            user_topic = ticker_symbol
            ticker_symbol = None
            company_data = None
        else:
            user_topic = ticker_symbol

       
        filename = re.sub(r'[^a-zA-Z0-9_]', '', user_topic.replace(' ', '_'))[:50].lower()
        
        
        user_prompt = create_prompt_template(user_topic, ticker_symbol)
        content = generate_long_report(user_prompt, target_words=5000)
        
        
        pdf_path = generate_pdf(content, filename, company_data, ticker_symbol)

        
        media_folder = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(media_folder, exist_ok=True)
        final_pdf_path = os.path.join(media_folder, f"{filename}.pdf")
        
        
        if os.path.exists(pdf_path):
            if os.path.exists(final_pdf_path):
                os.remove(final_pdf_path)  
            os.rename(pdf_path, final_pdf_path)  
        
        
        file_size = os.path.getsize(final_pdf_path) if os.path.exists(final_pdf_path) else 0
        file_size_str = f"{round(file_size / 1024, 2)} KB"  
        generated_at = datetime.now().isoformat()

        
        file_url = f"{settings.MEDIA_URL}reports/{filename}.pdf"

        
        response_data = {
            "url": request.build_absolute_uri(file_url),
            "fileName": f"{filename}.pdf",
            "generatedAt": generated_at,
            "fileSize": file_size_str,
        }

        return Response(response_data, status=200)
    except Exception as e:
        import logging
        logging.error(f"Error generating report: {str(e)}", exc_info=True)
        return Response(
            {"error": "Failed to generate report. Please try again later."}, 
            status=500
        )