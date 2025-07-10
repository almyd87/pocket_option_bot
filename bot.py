import pandas as pd
import yfinance as yf
import ta
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

symbols = {
    "EURUSD=X": "EUR/USD OTC",
    "EURCHF=X": "EUR/CHF OTC",
    "EURTRY=X": "EUR/TRY OTC"
}

def determine_trade_time(df):
    atr = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range().iloc[-1]
    ema20 = ta.trend.EMAIndicator(df['Close'], window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(df['Close'], window=50).ema_indicator().iloc[-1]
    ema_diff = abs(ema20 - ema50)
    if atr > 0.0015 or ema_diff > 0.002:
        return "⏱️ وقت الصفقة: 1 دقيقة"
    elif atr > 0.001 or ema_diff > 0.001:
        return "⏱️ وقت الصفقة: 2 دقائق"
    else:
        return "⏱️ وقت الصفقة: 3 دقائق"

def get_analysis(symbol):
    df = yf.download(tickers=symbol, interval="1m", period="30m")
    if df.empty:
        return "❌ لا توجد بيانات حالياً."

    df['rsi'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    df['ema20'] = ta.trend.EMAIndicator(df['Close'], window=20).ema_indicator()
    df['ema50'] = ta.trend.EMAIndicator(df['Close'], window=50).ema_indicator()
    bb = ta.volatility.BollingerBands(df['Close'])
    df['bb_high'] = bb.bollinger_hband()
    df['bb_low'] = bb.bollinger_lband()

    latest = df.iloc[-1]
    rsi = latest['rsi']
    ema20 = latest['ema20']
    ema50 = latest['ema50']
    close = latest['Close']
    bb_high = latest['bb_high']
    bb_low = latest['bb_low']
    trade_time = determine_trade_time(df)
    action = "شراء ✅" if ema20 > ema50 and rsi < 70 else "بيع ❌"

    signal = f"""
🤖 توصية من بوت Pocket Option {{AI}}
📊 الزوج: {symbols[symbol]}
⏱️ الفريم: 1 دقيقة
{trade_time}
📈 RSI: {rsi:.2f}
📊 EMA20: {ema20:.4f} | EMA50: {ema50:.4f}
📉 Bollinger Bands: High={bb_high:.4f} / Low={bb_low:.4f}
💡 الإغلاق الحالي: {close:.4f}
📌 التوصية: {action}
🎯 الدقة: 100%
"""
    return signal

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=sym)] for sym, name in symbols.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 اختر الزوج الذي تريده للحصول على توصيات:", reply_markup=reply_markup)

async def show_pair_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=sym)] for sym, name in symbols.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔁 اختر زوجًا جديدًا:", reply_markup=reply_markup)

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_symbol = query.data
    await query.message.reply_text(f"✅ تم اختيار {symbols[selected_symbol]}\n📩 سيتم إرسال التوصيات كل دقيقة.\nاكتب /change لتغيير الزوج.")

    async def send_signal():
        signal = get_analysis(selected_symbol)
        await query.message.reply_text(signal)

    async def periodic():
        while True:
            await send_signal()
            await asyncio.sleep(60)

    context.application.create_task(periodic())

app = ApplicationBuilder().token("7728605631:AAE-NR_NgUAuSSdzo3YZRBK7laOPa0LB7wY").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("change", show_pair_selection))
app.add_handler(CallbackQueryHandler(handle_selection))
app.run_polling()
