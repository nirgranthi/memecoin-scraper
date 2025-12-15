This source code is for evaluation and portfolio purposes only. Commercial use, modification, or distribution is strictly prohibited without purchasing a license. Contact me for licensing inquiries.

## Installation:
Clone it by running
```bash
git clone github.com/nirgranthi/memecoin-scraper
```
Or run it directly by running this command on cmd
```cmd
curl -o temp.py https://raw.githubusercontent.com/nirgranthi/memecoin-scraper/refs/heads/main/sol_scraper.py && python temp.py && del temp.py
```

## Requirement:

* **Token address** Get token address, not pair address. For example, on [Dexscreener](https://dexscreener.com/), copy the address that has the token's name beside it.

## Use:
1. Enter token address when asked.
2. Choose from the given timeframes (e.g., 1m, 5m, 15m, 1h, 4h, 12h, 1d).
3. Choose the option with favourable liquidity by entering the number corresponding to them.
4. It will now start fetching all the candle ohlcv data, it will be saved in a json file named after the token address and selected timeframe.
5. Upload that json file to advance llm(Gemini 3 pro, ChatGPT, etc) for analysis.
   **You can use these given prompts**
```Deep dive analysis
Act as a professional crypto analyst. Analyze the attached JSON file containing 5-minute candle data for this Solana token.
1. Trend Analysis: Is the overall trend Bullish, Bearish, or Sideways based on the close prices?
2. Volume Check: Look at the volume field. Is the volume increasing with price (organic) or decreasing while price rises (manipulation/weakness)?
3. Volatility: Are the candle bodies (difference between Open and Close) unusually large indicating instability?
4. Verdict: Based on the data, is this a 'Buy', 'Wait', or 'Stay Away'?
```
```Scam/Pump and Dump detector
Analyze this data for signs of a 'Pump and Dump' scheme.
1. Check for massive spikes in price followed by immediate massive drops in the next few candles.
2. Calculate the drop percentage from the All-Time High (ATH) in this dataset to the current price.
3. Is the liquidity/volume drying up in the most recent candles compared to the start?
4. Tell me bluntly: Does this look like organic growth or a trap?
```
```Technical analysis
Perform a technical analysis on this JSON data.
1. RSI Calculation: Estimate the Relative Strength Index (RSI 14) for the last 5 candles. Is it Overbought (>70) or Oversold (<30)?
2. Support/Resistance: Identify the key support level (lowest low that held) and resistance level (highest high).
3. Risk/Reward: If I buy at the last 'close' price, what is the potential downside risk percentage?
```


## Avoid getting rugpulled by making sure that
- Socials should exist
- Liquidity pool should be burned
- Top 10 holders should not hold a large amount of the coin
- Minting authority should be revoked
- Watch YouTube videos on avoid bad memecoins


## Visualizing the data
* Once you have the json file, head here
* <a href="https://nirgranthi.github.io/memecoin-scraper/" target="_blank"><img src="https://img.shields.io/badge/🚀_Live_Demo-Start_Here-3b82f6?style=for-the-badge&logo=github&logoColor=white" alt="Live Demo" height="40" /></a>
* Upload the json file by clicking "Upload JSON" on the top, done.
* You will get a dexscreener inspired candle chart.

