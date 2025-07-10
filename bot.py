import pandas as pd
import yfinance as yf
import ta
import asyncio
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

# ✅ الأزواج المدعومة
symbols = {
    "EURUSD=X": "EUR/USD OTC",
    "EURCHF=X": "EUR/CHF OTC",
    "EURTRY=X": "EUR/TRY OTC",
    "EURJPY=X": "EUR/JPY OTC",
    "EURAUD=X": "EUR/AUD OTC",
    "EURCAD=X": "EUR/CAD OTC"
}

# 🕓 فلتر وقت التوصية: من 7 صباحًا حتى 7 مساءً UTC
def is_market_open():
    current_hour = datetime.utcnow().hour
    return 7 <= current_hour <= 19

# ⚙️ التحليل والتوصية
def get_analysis(symbol):
    df = yf.download(tickers=symbol, interval="1m", period="45m")
    if df.empty or len(df) < 30:
        return "📛 لا توجد بيانات كافية الآن — الانتظار..."

    # المؤشرات
    df['rsi'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    df['ema20'] = ta.trend.EMAIndicator(df['Close'], window=20).ema_indicator()
    df['ema50'] = ta.trend.EMAIndicator(df['Close'], window=50).ema_indicator()
    macd = ta.trend.MACD(df['Close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    stoch = ta.momentum.StochRSIIndicator(df['Close'])
    df['stoch'] = stoch.stochrsi()
    df['adx'] = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close']).adx()
    bb = ta.volatility.BollingerBands(df['Close'])
    df['bbh'] = bb.bollinger_hband()
    df['bbl'] = bb.bollinger_lband()

    latest = df.iloc[-1]
    rsi = latest['rsi']
    ema20 = latest['ema20']
    ema50 = latest['ema50']
    macd_val = latest['macd']
    macd_signal = latest['macd_signal']
    stoch_val = latest['stoch']
    adx = latest['adx']
    close = latest['Close']
    bb_high = latest['bbh']
    bb_low = latest['bbl']

    # 💡 اتخاذ القرار (بدون فلترة)
    if ema20 > ema50 and macd_val > macd_signal and rsi < 70:
        signal = "✅ *شراء*"
    elif ema20 < ema50 and macd_val < macd_signal and rsi > 30:
        signal = "❌ *بيع*"
    else:
        signal = "🟡 *انتظار*"

    # 📩 التوصية المفصلة
    return f"""
🤖 *توصية جديدة - Pocket Option AI*
━━━━━━━━━━━━━━━
📊 الزوج: *{symbols[symbol]}*
🕒 الفريم: *1 دقيقة*
━━━━━━━━━━━━━━━
📈 RSI: {rsi:.2f}
📊 EMA20: {ema20:.5f}
📊 EMA50: {ema50:.5f}
📉 MACD: {macd_val:.5f}
📉 Signal Line: {macd_signal:.5f}
⚡ ADX: {adx:.2f}
🎯 Stochastic RSI: {stoch_val:.2f}
🔽 Bollinger Bands:
 • High: {bb_high:.5f}
 • Low: {bb_low:.5f}
💰 الإغلاق الحالي: {close:.5f}
━━━━━━━━━━━━━━━
📌 التوصية: {signal}
    """

# 🔘 أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=sym)] for sym, name in symbols.items()]
    await update.message.reply_text("👋 اختر زوج العملة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_pair_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=sym)] for sym, name in symbols.items()]
    await update.message.reply_text("🔁 اختر زوجًا جديدًا:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data
    await query.message.reply_text(f"✅ تم اختيار *{symbols[symbol]}*.\n📩 سيتم إرسال توصية كل دقيقة.\nاكتب /change لتبديل الزوج.", parse_mode="Markdown")

    async def send_periodic_signals():
        while True:
            if is_market_open():
                signal = get_analysis(symbol)
                await query.message.reply_text(signal, parse_mode="Markdown")
            else:
                await query.message.reply_text("⏳ السوق مغلق حاليًا (خارج ساعات العمل)", parse_mode="Markdown")
            await asyncio.sleep(60)

    context.application.create_task(send_periodic_signals())

# 🧠 تشغيل البوت
app = ApplicationBuilder().token("7728605631:AAE-NR_NgUAuSSdzo3YZRBK7laOPa0LB7wY").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("change", show_pair_selection))
app.add_handler(CallbackQueryHandler(handle_selection))
app.run_polling()
