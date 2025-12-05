import requests
import json
import time
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
# Supported Timeframes by Free APIs: 1m, 5m, 15m, 1h, 4h, 12h, 1d. 
#1s and 30s are NOT available for free.
TIMEFRAME_MAP = {
    '1m': 'minute',
    '5m': 'minute',
    '15m': 'minute',
    '1h': 'hour',
    '4h': 'hour',
    '12h': 'hour',
    '1d': 'day'
}

def get_best_pair(token_address):
    """
    DexScreener se favourable pair address find karna hai.
    direct pair address se bhi krne ka option tha lekin mujhe ye hi sahi laga
    """
    global name
    global symbol
    print(f"🔍 Finding best liquidity pool for: {token_address}...")
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    
    try:
        response = requests.get(url).json()
        if not response.get('pairs'):
            return None
        
        # Filter for Solana chain only
        sol_pairs = [p for p in response['pairs'] if p['chainId'] == 'solana']
        
        if not sol_pairs:
            print("❌ No Solana pairs found.")
            return None
        
        # Sort by Liquidity to get the main pair
        print(f'{len(sol_pairs)} pairs found')
        #print(sol_pairs)
        if len(sol_pairs)==1:
            #pahla pair
            best_pair = sol_pairs[0]
        else:
            try:
                f=1
                for pair in sol_pairs:
                    # 0 liquidity means not found
                    print(f'{f}:  Liquidity:${str(pair.get('liquidity', {}).get('usd', 0))} on {pair.get('dexId')}')
                    f+=1
                num = int(input('\nChoose pair (e.g. 1,2,3...): '))
                best_pair = sol_pairs[num-1]
                #comment line 50 to 56 and uncomment line 58 if you want to automatically select pair with highest liquidity
                #best_pair = sorted(sol_pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0), reverse=True)[0]
            except Exception as e:
                    print(e)
                    print('Invalid input. Choosing pair with highest liquidity...')
                    best_pair = sorted(sol_pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0), reverse=True)[0]
        name = best_pair.get('baseToken').get('name')
        symbol = best_pair.get('baseToken').get('symbol')
        print(f"✅ Found Pair: {best_pair['pairAddress']} on {best_pair['dexId']}")
        return best_pair['pairAddress']
        
    except Exception as e:
        print(f"❌ Error fetching pair: {e}")
        return None

def fetch_full_history(pair_address, timeframe_input, agrg_value):
    """
    recursive type shi algo(pagination) for getting all the candles from free geckoterminal API
    """
    base_url = f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pair_address}/ohlcv/{timeframe_input}?aggregate={agrg_value}&limit=1000"
    
    all_ohlcv = []
    next_timestamp = None
    page = 1
    
    print(f"⏳ Downloading full history ({timeframe_input})... This may take time.")
    
    while True:
        # Construct URL with pagination if needed
        # GeckoTerminal free API standard limit is usually 100-1000 candles per call but i cant get more than 100 I don't why
        # We append 'limit=1000' to maximize data per call
        url = base_url
        if next_timestamp:
            url = f"{base_url}&before_timestamp={next_timestamp}"
            
        try:
            # Gecko free api allows only 30 calls per minute
            time.sleep(2) 
            
            resp = requests.get(url)
            
            if resp.status_code == 404:
                print("❌ Pool not found on GeckoTerminal history yet (Too new?).")
                break
                
            if resp.status_code == 429:
                print("⚠️ Rate limit hit. Waiting 10 seconds...")
                time.sleep(10)
                continue
                
            data = resp.json()
            
            # Extracting OHLCV list
            # Format: [timestamp, open, high, low, close, volume]
            ohlcv_list = data.get('data', {}).get('attributes', {}).get('ohlcv_list', [])
            
            if not ohlcv_list:
                print("✅ Reached end of history.")
                break
                
            # Add to our main list
            all_ohlcv.extend(ohlcv_list)
            first_date = datetime.fromtimestamp(ohlcv_list[0][0]).strftime('%Y-%m-%d %H:%M')
            last_date = datetime.fromtimestamp(ohlcv_list[-1][0]).strftime('%Y-%m-%d %H:%M')
            print(f"   -> Page {page}: Fetched {len(ohlcv_list)} candles. Range: {first_date} to {last_date}")
            
            # Pagination Logic: Update timestamp for next loop (Last candle's time)
            last_candle_time = ohlcv_list[-1][0]
            
            # Break if we aren't getting new data or loop seems stuck
            if next_timestamp == last_candle_time:
                break
                
            next_timestamp = last_candle_time
            page += 1
            
            # Safety break for massive histories to prevent infinite loops (optional)
            if page > 50: 
                print("⚠️ Safety limit reached (50 pages). Stopping.")
                break
                
        except Exception as e:
            print(f"❌ Error fetching history: {e}")
            break
    #print(url)
    return all_ohlcv

def save_to_json(name, symbol, token_address, pair_address, data, timeframe):
    """
    Clean formatted JSON export
    """
    if not data:
        print("❌ No data to save.")
        return

    # Organize data for AI Analysis
    structured_data = {
        "meta": {
            "name": name,
            "symbol": symbol,
            "token_address": token_address,
            "pair_address": pair_address,
            "network": "solana",
            "timeframe": timeframe,
            "download_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "candle_count": len(data),
            "note": "Data format: [Timestamp, Open, High, Low, Close, Volume]"
        },
        "candles": []
    }

    # Convert raw list to labeled objects (easier for AI to read)
    for candle in data:
        structured_data["candles"].append({
            "timestamp": candle[0],
            "date_readable": datetime.fromtimestamp(candle[0]).strftime('%Y-%m-%d %H:%M:%S'),
            "open": candle[1],
            "high": candle[2],
            "low": candle[3],
            "close": candle[4],
            "volume": candle[5]
        })

    filename = f"{token_address}_{timeframe}_full_history.json"
    
    with open(filename, 'w') as f:
        json.dump(structured_data, f, indent=4)
        
    print(f"\n🎉 SUCCESS! Data saved to: {filename}")
    print(f"📊 Total Candles: {len(data)}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- SOL MEMECOIN HISTORY SCRAPER ---")
    token_addr = input("Enter SOL Token Address: ").strip()
    
    print("\nAvailable Timeframes: 1m, 5m, 15m, 1h, 4h, 12h, 1d")
    #Note: 1s/30s are not available on free tier directly. Raise Issue if wanted
    tf_input = input("Enter Timeframe (e.g., 1m, 5m, 4h): ").strip().lower()

    # Map input to API allowed values
    api_tf = TIMEFRAME_MAP.get(tf_input)
    if tf_input == '1m': api_tf, aggregate = 'minute', 1
    if tf_input == '5m': api_tf, aggregate = 'minute', 5
    if tf_input == '15m': api_tf, aggregate = 'minute', 15
    if tf_input == '1h': api_tf, aggregate = 'hour', 1
    if tf_input == '4h': api_tf, aggregate = 'hour', 4
    if tf_input == '12h': api_tf, aggregate = 'hour', 12
    if tf_input == '1d': api_tf, aggregate = 'day', 1
    
    # 1. Get Pair Address
    pair_addr = get_best_pair(token_addr)
    
    if pair_addr:
        # 2. Get History
        history = fetch_full_history(pair_addr, api_tf, aggregate)
        
        # 3. Save
        save_to_json(name, symbol, token_addr, pair_addr, history, tf_input)
    else:
        print("❌ Could not proceed without a valid Pair Address.")
    
