import re
import time
from typing import Optional, Dict
from decimal import Decimal

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import yfinance as yf
    yf.set_tz_cache_location("/tmp/yfinance_cache")
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

BRAPI_BASE_URL = "https://brapi.dev/api"


def extract_ticker_from_description(description: str) -> Optional[str]:
    """
    Extrai o ticker de uma descricao de transacao.
    Procura por padroes comuns de tickers brasileiros (PETR4, VALE3, etc)
    e internacionais (AAPL, MSFT, etc).
    """
    patterns = [
        r'\b([A-Z]{4}[0-9]{1,2})\b',
        r'\b([A-Z]{3}[0-9]{1,2})\b',
        r'\b([A-Z]{4,5})\b',
    ]
    
    description_upper = description.upper()
    
    for pattern in patterns:
        match = re.search(pattern, description_upper)
        if match:
            ticker = match.group(1)
            if len(ticker) >= 4 and any(c.isdigit() for c in ticker):
                return ticker
            if len(ticker) >= 4 and ticker.isalpha():
                return ticker
    
    return None


def get_stock_price_brapi(ticker: str) -> Optional[float]:
    """
    Busca o preco usando BrapiDev API.
    Nota: API pode exigir token de autenticacao.
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    try:
        ticker_clean = ticker.upper().strip().replace('.SA', '')
        url = f"{BRAPI_BASE_URL}/quote/{ticker_clean}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("error") and data.get("results") and len(data["results"]) > 0:
                price = data["results"][0].get("regularMarketPrice")
                if price and float(price) > 0:
                    return float(price)
    except Exception:
        pass
    
    return None


def get_stock_price_statusinvest(ticker: str) -> Optional[float]:
    """
    Fallback usando scraping simples do StatusInvest.
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    try:
        ticker_clean = ticker.upper().strip().replace('.SA', '')
        
        if is_fii_ticker(ticker_clean):
            url = f"https://statusinvest.com.br/fundos-imobiliarios/{ticker_clean.lower()}"
        else:
            url = f"https://statusinvest.com.br/acoes/{ticker_clean.lower()}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            match = re.search(r'<strong class="value">([0-9.,]+)</strong>', response.text)
            if match:
                price_str = match.group(1)
                price_str = price_str.replace('.', '').replace(',', '.')
                price = float(price_str)
                if price > 0:
                    return price
    except Exception:
        pass
    
    return None


def get_stock_price_yfinance(ticker: str, retry_count: int = 2) -> Optional[float]:
    """
    Busca o preco atual de uma acao usando yfinance.
    Tenta com .SA e BVMF: para acoes brasileiras.
    """
    if not YFINANCE_AVAILABLE:
        return None
    
    ticker_upper = ticker.upper().strip().replace('.SA', '')
    
    symbols_to_try = [
        f"{ticker_upper}.SA",
        f"BVMF:{ticker_upper}",
    ]
    if not re.match(r'^[A-Z]{4}\d{1,2}$', ticker_upper):
        symbols_to_try.append(ticker_upper)
    
    for symbol in symbols_to_try:
        for attempt in range(retry_count):
            try:
                stock = yf.Ticker(symbol)
                
                try:
                    info = stock.info
                    if info and isinstance(info, dict):
                        price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
                        if price and float(price) > 0:
                            return float(price)
                except Exception:
                    pass
                
                try:
                    hist = stock.history(period="5d")
                    if hist is not None and not hist.empty and 'Close' in hist.columns:
                        price = float(hist['Close'].iloc[-1])
                        if price > 0:
                            return price
                except Exception:
                    pass
                
                break
            except Exception:
                if attempt < retry_count - 1:
                    time.sleep(0.5)
                continue
    
    return None


def get_stock_price_yahoo_direct(ticker: str) -> Optional[float]:
    """
    Busca direta no Yahoo Finance via requests (sem yfinance).
    Tenta com .SA e tambem com BVMF: como fallback.
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    ticker_clean = ticker.upper().strip().replace('.SA', '')
    
    symbols_to_try = [
        f"{ticker_clean}.SA",
        f"BVMF:{ticker_clean}",
        ticker_clean
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for symbol in symbols_to_try:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {'interval': '1d', 'range': '5d'}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('chart', {}).get('result', [])
                if result and len(result) > 0:
                    meta = result[0].get('meta', {})
                    price = meta.get('regularMarketPrice')
                    if price and float(price) > 0:
                        return float(price)
        except Exception:
            continue
    
    return None


def get_stock_price_google(ticker: str) -> Optional[float]:
    """
    Busca preco via Google Finance (scraping da pagina).
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    ticker_clean = ticker.upper().strip().replace('.SA', '')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        url = f"https://www.google.com/finance/quote/BVMF:{ticker_clean}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            match = re.search(r'R\$([0-9]+[.,][0-9]+)', response.text)
            if match:
                price_str = match.group(1).replace(',', '.')
                price = float(price_str)
                if price > 0:
                    return price
            
            match = re.search(r'data-last-price="([0-9.]+)"', response.text)
            if match:
                price = float(match.group(1))
                if price > 0:
                    return price
    except Exception:
        pass
    
    return None


def is_brazilian_ticker(ticker: str) -> bool:
    """Verifica se o ticker parece ser brasileiro (acoes ou FIIs)."""
    ticker_upper = ticker.upper().strip()
    return bool(re.match(r'^[A-Z]{4}[0-9]{1,2}$', ticker_upper))


def is_fii_ticker(ticker: str) -> bool:
    """Verifica se e um FII (termina em 11)."""
    ticker_upper = ticker.upper().strip()
    return ticker_upper.endswith('11') and len(ticker_upper) >= 5


def get_stock_price(ticker: str) -> Optional[float]:
    """
    Busca o preco atual de uma acao.
    Tenta multiplas fontes em ordem de confiabilidade:
    1. StatusInvest (BR)
    2. Google Finance (BVMF:)
    3. Yahoo Direct (com fallback BVMF:)
    4. yfinance
    5. BrapiDev
    """
    ticker_upper = ticker.upper().strip()
    
    if is_brazilian_ticker(ticker_upper):
        price = get_stock_price_statusinvest(ticker_upper)
        if price:
            return price
        
        price = get_stock_price_google(ticker_upper)
        if price:
            return price
        
        price = get_stock_price_yahoo_direct(ticker_upper)
        if price:
            return price
    
    price = get_stock_price_yfinance(ticker_upper)
    if price:
        return price
    
    price = get_stock_price_brapi(ticker_upper)
    if price:
        return price
    
    return None


def get_multiple_prices(tickers: list) -> Dict[str, Optional[float]]:
    """
    Busca precos de multiplas acoes.
    """
    prices = {}
    for ticker in tickers:
        prices[ticker] = get_stock_price(ticker)
    return prices


def detect_investment_type(ticker: str) -> str:
    """
    Detecta o tipo de investimento baseado no ticker.
    """
    ticker_upper = ticker.upper()
    
    if ticker_upper.endswith('11') and len(ticker_upper) >= 5:
        return "fii"
    
    if ticker_upper in ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'AVAX', 'MATIC', 'LINK', 'UNI', 'DOGE', 'SHIB', 'XRP', 'BNB']:
        return "crypto"
    
    if re.match(r'^[A-Z]{4}[0-9]{1,2}$', ticker_upper):
        return "stock"
    
    return "other"
