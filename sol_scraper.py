import requests
import json
import time
import sys
import os
from datetime import datetime

# --- CONFIGURATION ---
TIMEFRAME_MAP = {
    '1m': 'minute', '5m': 'minute', '15m': 'minute',
    '1h': 'hour', '4h': 'hour', '12h': 'hour', '1d': 'day'
}

def clean_filename(symbol, token_address, timeframe):
    #Generates a consistent filename
    safe_symbol = "".join([c for c in symbol if c.isalnum() or c in ('_','-')])
    return f"{safe_symbol}_{token_address}_{timeframe}.json"

def get_best_pair(token_address, interactive=False):
    """
    If interactive=True and multiple pairs exist, asks user to choose.
    Else, auto-selects highest liquidity.
    """
    print(f"🔍 Finding liquidity pools for: {token_address}...")
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    
    try:
        response = requests.get(url).json()
        if not response.get('pairs'): return None, None, None
        
        sol_pairs = [p for p in response['pairs'] if p['chainId'] == 'solana']
        if not sol_pairs: return None, None, None
        
        # Sort by Liquidity (Highest first)
        sorted_pairs = sorted(sol_pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0), reverse=True)
        
        best_pair = None
        
        # If interactive mode and multiple pairs, ask user.
        if interactive and len(sorted_pairs) > 1:
            print(f"\nFound {len(sorted_pairs)} pairs. Please select one:")
            for i, pair in enumerate(sorted_pairs[:10]): # Show top 10
                liq = pair.get('liquidity', {}).get('usd', 0)
                dex = pair.get('dexId')
                symbol = pair.get('baseToken', {}).get('symbol')
                print(f"{i+1}: {symbol} on {dex} | Liquidity: ${liq:,.2f} | Addr: {pair['pairAddress']}")
            
            try:
                choice = input("\nChoose pair number (default 1): ").strip()
                if not choice: choice = 1
                idx = int(choice) - 1
                if 0 <= idx < len(sorted_pairs):
                    best_pair = sorted_pairs[idx]
                else:
                    print("Invalid selection, using top pair.")
                    best_pair = sorted_pairs[0]
            except:
                print("Invalid input, defaulting to top pair.")
                best_pair = sorted_pairs[0]
        else:
            # Auto-mode or single pair
            best_pair = sorted_pairs[0]
            if interactive: 
                print(f"-> Auto-selected top pair: {best_pair['pairAddress']}")

        name = best_pair.get('baseToken', {}).get('name', 'Unknown')
        symbol = best_pair.get('baseToken', {}).get('symbol', 'Unknown')
        print(f"✅ Selected Pair: {best_pair['pairAddress']} ({symbol})")
        return best_pair['pairAddress'], name, symbol

    except Exception as e:
        print(f"❌ Error fetching pair: {e}")
        return None, None, None

def fetch_candles(pair_address, timeframe, aggregate, start_timestamp=None, end_timestamp=None, limit_stop=False):
    """
    Generic fetcher with pagination and overlap checks.
    """
    base_url = f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pair_address}/ohlcv/{timeframe}"
    params = {'aggregate': aggregate, 'limit': 1000}
    
    fetched_data = []
    next_ts = start_timestamp
    page = 1
    
    stop_label = " (Stop at existing)" if limit_stop else ""
    print(f"   ⏳ Fetching batch{stop_label}...")

    while True:
        current_params = params.copy()
        if next_ts:
            current_params['before_timestamp'] = next_ts
            
        try:
            time.sleep(2.1) # Safe buffer
            resp = requests.get(base_url, params=current_params)
            
            if resp.status_code == 429:
                print("      ⚠️ Rate limit. Pausing 10s...")
                time.sleep(10)
                continue
            if resp.status_code != 200:
                print(f"      ⚠️ API Error {resp.status_code}")
                break
                
            data = resp.json()
            ohlcv_list = data.get('data', {}).get('attributes', {}).get('ohlcv_list', [])
            
            if not ohlcv_list: break
            
            # --- OVERLAP LOGIC ---
            valid_batch = []
            stop_fetching = False
            
            for candle in ohlcv_list:
                ts = candle[0]
                # If we are downloading NEW data (going backwards from now), 
                # stop when we hit the timestamp of data we already have.
                if end_timestamp and ts <= end_timestamp:
                    stop_fetching = True
                    continue 
                valid_batch.append(candle)
            
            fetched_data.extend(valid_batch)
            
            range_start = datetime.fromtimestamp(ohlcv_list[0][0]).strftime('%Y-%m-%d %H:%M')
            range_end = datetime.fromtimestamp(ohlcv_list[-1][0]).strftime('%Y-%m-%d %H:%M')
            print(f"      -> Page {page}: Got {len(valid_batch)} new candles. ({range_start} -> {range_end})")

            if stop_fetching and limit_stop:
                print("      ✅ Merged with existing history. Stopping phase.")
                break

            last_ts = ohlcv_list[-1][0]
            if next_ts == last_ts: break
            next_ts = last_ts
            page += 1
            
            if page > 50: 
                print("      ⚠️ Safety limit (50 pages) reached.")
                break
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            break
            
    return fetched_data

def process_data(token_addr, tf_input, interactive=False):
    # 1. Validation & Setup
    api_tf = TIMEFRAME_MAP.get(tf_input, 'day')
    aggregate = 1
    if tf_input == '1m': api_tf, aggregate = 'minute', 1
    elif tf_input == '5m': api_tf, aggregate = 'minute', 5
    elif tf_input == '15m': api_tf, aggregate = 'minute', 15
    elif tf_input == '1h': api_tf, aggregate = 'hour', 1
    elif tf_input == '4h': api_tf, aggregate = 'hour', 4
    elif tf_input == '12h': api_tf, aggregate = 'hour', 12
    elif tf_input == '1d': api_tf, aggregate = 'day', 1

    pair_addr, name, symbol = get_best_pair(token_addr, interactive=interactive)
    if not pair_addr: return

    filename = clean_filename(symbol, token_addr, tf_input)
    
    existing_candles = []
    min_ts = None
    max_ts = None
    
    # 2. Check Existing File
    if os.path.exists(filename):
        print(f"\n📂 Found existing file: {filename}")
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                existing_candles = data.get('candles', [])
                
            if existing_candles:
                # Extract timestamps to find gaps
                # Handling both list format [ts, o, h, l, c, v] and dict format
                timestamps = []
                for c in existing_candles:
                    if isinstance(c, dict): timestamps.append(c['timestamp'])
                    elif isinstance(c, list): timestamps.append(c[0])
                
                if timestamps:
                    min_ts = min(timestamps)
                    max_ts = max(timestamps)
                    print(f"   📅 Data Range: {datetime.fromtimestamp(min_ts)} to {datetime.fromtimestamp(max_ts)}")
        except Exception as e:
            print(f"   ⚠️ Error reading file, starting fresh. {e}")
            existing_candles = []

    new_candles_future = []
    new_candles_history = []
    
    # Phase 1: Download NEW data (From Now -> Back to Max Existing TS)
    if max_ts:
        print("\n🚀 Phase 1: Updating Recent Data...")
        new_candles_future = fetch_candles(pair_addr, api_tf, aggregate, start_timestamp=None, end_timestamp=max_ts, limit_stop=True)
    else:
        print("\n🚀 Phase 1: Downloading Fresh Data...")
        new_candles_future = fetch_candles(pair_addr, api_tf, aggregate, start_timestamp=None, end_timestamp=None, limit_stop=False)

    # Phase 2: Download OLD data (From Min Existing TS -> Back to Genesis)
    if min_ts:
        print("\n📜 Phase 2: Backfilling History...")
        new_candles_history = fetch_candles(pair_addr, api_tf, aggregate, start_timestamp=min_ts, end_timestamp=None, limit_stop=False)
    
    # 3. Merging
    print("\n🔄 Merging datasets...")
    final_dict = {}

    def add_list(candle_list):
        count = 0
        for item in candle_list:
            if isinstance(item, dict):
                ts = item['timestamp']
                obj = item
            else:
                ts = item[0]
                obj = {
                    "timestamp": item[0],
                    "date_readable": datetime.fromtimestamp(item[0]).strftime('%Y-%m-%d %H:%M:%S'),
                    "open": item[1], "high": item[2], "low": item[3], "close": item[4], "volume": item[5]
                }
            final_dict[ts] = obj
            count += 1
        return count

    c1 = add_list(existing_candles)
    c2 = add_list(new_candles_future)
    c3 = add_list(new_candles_history)
    
    print(f"   Stats: {c1} existing + {c2} new recent + {c3} older fetched.")
    
    sorted_candles = sorted(final_dict.values(), key=lambda x: x['timestamp'])
    
    # 4. Save
    output_data = {
        "meta": {
            "name": name,
            "symbol": symbol,
            "token_address": token_addr,
            "pair_address": pair_addr,
            "timeframe": tf_input,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_candles": len(sorted_candles)
        },
        "candles": sorted_candles
    }
    
    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=4)
        
    print(f"\n🎉 DONE! Saved {len(sorted_candles)} candles to: {filename}")

if __name__ == "__main__":
    if len(sys.argv) == 3:
        # Automation Mode (Arguments detected)
        t_addr = sys.argv[1]
        t_frame = sys.argv[2]
        process_data(t_addr, t_frame, interactive=False)
    else:
        # Interactive Mode (No arguments)
        print("--- SOL SCRAPER ULTIMATE ---")
        try:
            t_addr = input("Enter Token Address: ").strip()
            if not t_addr: sys.exit("Address required.")
            
            print("Timeframes: 1m, 5m, 15m, 1h, 4h, 12h, 1d")
            t_frame = input("Enter Timeframe: ").strip().lower()
            if not t_frame: t_frame = '1d'
            
            process_data(t_addr, t_frame, interactive=True)
        except KeyboardInterrupt:
            print("\nCancelled.")