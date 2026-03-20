import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
from datetime import datetime
import threading
from flask import Flask

# ==========================================
# ⚙️ SOZLAMALAR (To'ldirildi!)
# ==========================================
TELEGRAM_BOT_TOKEN = '8342743301:AAGJo82_CwCoU26VL5n2TM49qAtPCSkt2E8'
TELEGRAM_CHANNEL_ID = '-1003810699140'
TIMEFRAME = '15m'       # Taymfreym (pump uchun 15m)
RISK_REWARD = 3         # 1:3 RR nisbat

# Binance birjasini ulash
exchange = ccxt.binance({'enableRateLimit': True})

# ==========================================
# 🌐 KEEP-ALIVE WEB SERVER (Replit / UptimeRobot uchun)
# ==========================================
app = Flask(name)

@app.route('/')
def home():
    return "🚀 Signal Bot is Alive and Scanning Market!"

def run_server():
    # Faqat 0.0.0.0 va port orqali Replitda ishlashini taminlaymiz
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()


# ==========================================
# 🤖 BOTNING ASOSIY MANTIG'I
# ==========================================
def send_telegram_signal(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': msg,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Internet/Telegram xatolik: {e}")

def get_data(symbol, limit=100):
    try:
        bars = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except:
        return None

def analyze_and_signal(symbol):
    df = get_data(symbol, limit=100)
    if df is None or len(df) < 50:
        return
        
    # Indikatorlarni hisoblash
    adx_df = df.ta.adx(length=14)
    if adx_df is not None:
        df = pd.concat([df, adx_df], axis=1)
    
    df.ta.ema(length=9, append=True)
    df.ta.ema(length=21, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.atr(length=14, append=True)
    
    last_row = df.iloc[-1]
    
    if pd.isna(last_row.get('RSI_14')) or pd.isna(last_row.get('MACD_12_26_9')):
        return

    close_price = last_row['close']
    atr = last_row.get('ATRr_14', close_price * 0.01)
    
    adx = last_row.get('ADX_14', 0)
    ema9 = last_row.get('EMA_9', 0)
    ema21 = last_row.get('EMA_21', 0)
    rsi = last_row.get('RSI_14', 0)
    macd = last_row.get('MACD_12_26_9', 0)
    macd_signal = last_row.get('MACDs_12_26_9', 0)
    bb_mid = last_row.get('BBM_20_2.0', 0)

    # 5 ta Qat'iy tasdiq (LONG)
    cond1 = adx > 25
    cond2 = ema9 > ema21
    cond3 = 50 < rsi < 70
    cond4 = macd > macd_signal and macd > 0
    cond5 = close_price > bb_mid
    
    if cond1 and cond2 and cond3 and cond4 and cond5:
        # TP va SL ATR orqali
        stop_loss = close_price - (atr * 1.5)
        take_profit = close_price + (atr * 4.5)
        
        sl_percent = ((close_price - stop_loss) / close_price) * 100
        tp_percent = ((take_profit - close_price) / close_price) * 100
        
        if sl_percent > 4.0:
            return

        signal_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
[3/20/2026 8:48 PM] Saidislom: msg = (
            f"🚀 <b>PUMP SIGNAL ANIQANDI!</b>\n\n"
            f"💠 <b>Juftlik:</b> #{symbol.replace('/', '')}\n"
            f"🛒 <b>Aksiya:</b> L O N G 🟢\n"
            f"🕰 <b>Vaqt:</b> {signal_time}\n"
            f"📉 <b>Taymfreym:</b> {TIMEFRAME}\n\n"
            f"💵 <b>Kirish narxi:</b> {close_price:.4f}\n"
            f"🎯 <b>Take-Profit:</b> {take_profit:.4f} (+{tp_percent:.2f}%)\n"
            f"🛑 <b>Stop-Loss:</b> {stop_loss:.4f} (-{sl_percent:.2f}%)\n\n"
            f"📊 <b>Nisbat (RR):</b> 1:{RISK_REWARD}\n"
            f"🧮 <b>Tasdiqlar:</b> ADX, EMA, RSI, BB, MACD (5/5)\n"
            f"⚡️ @Mening_Kanalim (Avto-Bot)" # Kanal linkini o'zgartirishingiz mumkin!
        )
        
        print(f"[{signal_time}] Yuborildi: {symbol}")
        send_telegram_signal(msg)
        return True
    return False

def main():
    print("🤖 VIP Signal Bot ishga tushdi... Market analiz qilinmoqda.")
    
    # Asosiy kuchli harakatlanadigan USDT juftliklari
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 
               'AVAX/USDT', 'LINK/USDT', 'MATIC/USDT', 'DOT/USDT', 'LTC/USDT', 'NEAR/USDT', 'ATOM/USDT', 
               'FTM/USDT', 'SAND/USDT', 'MANA/USDT', 'GALA/USDT', 'PEPE/USDT', 'SHIB/USDT']
               
    cooldown = {}
    
    while True:
        for sym in symbols:
            if sym in cooldown and (time.time() - cooldown[sym]) < 7200:
                continue
                
            try:
                is_signaled = analyze_and_signal(sym)
                if is_signaled:
                    cooldown[sym] = time.time()
            except Exception as e:
                pass
                
            time.sleep(1)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sikl yakunlandi. Navbatdagi analiz kutilyapti...")
        time.sleep(60 * 5)

if name == 'main':
    # Flask web serverni ishga tushiramiz (UptimeRobot ping qilishi uchun!)
    keep_alive()
    # Va bot analizini davom ettiramiz
    main()
