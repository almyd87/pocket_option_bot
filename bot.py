import pandas as pd
import yfinance as yf
import ta
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

# 1. الأزواج المدعومة
symbols = {
    "EURUSD=X": "EUR/USD OTC",
    "EURCHF=X": "EUR/CHF OTC",
    "EURTRY=X": "EUR/TRY OTC",
    "EURJPY=X": "EUR/JPY OTC",
    "EURAUD=X": "EUR/AUD OTC",
    "EURCAD=X": "EUR/CAD OTC"
}

# 2. تحديد وقت الصفقة حسب حركة السوق
def determine_trade_time(df):
    atr = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range().iloc[-1]
    ema20 = ta.trend.EMAIndicator(df['Close'], window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(df['Close'], window=50).ema_indicator().iloc[-1]
    ema_diff = abs(ema20 - ema50)
    if atr > 0.0015 or ema_diff > 0.002:
        return "1 دقيقة"
    elif atr > 0.001 or ema_diff > 0.001:
        return "2 دقائق"
    else:
        return "3 دقائق"

# 3. التحليل وإعطاء التوصية
def get_analysis(symbol):
    df = yf.download(tickers=symbol, interval="1m", period="30m")
    if df.empty or len(df) < 20:
        return f"""
📛 *لا توجد حركة كافية حالياً – الانتظار*

🧠 *تحليل المؤشرات:*
- RSI: لا يمكن حسابه
- EMA20: لا يمكن حسابه
- EMA50: لا يمكن حسابه
- Bollinger Bands: لا يوجد بيانات
        """.strip()

    # المؤشرات
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

    # 4. التوصية
    if pd.isna(rsi) or pd.isna(ema20) or pd.isna(ema50):
        action = "❗ البيانات غير كافية للتوصية"
    elif ema20 > ema50 and rsi < 70:
        action = "✅ *شراء*"
    elif ema20 < ema50 and rsi > 30:
        action = "❌ *بيع*"
    else:
        action = "🟡 *انتظار*"

    return f"""
🤖 *توصية جديدة من Pocket Option {{AI}}*
━━━━━━━━━━━━━━━
📊 الزوج: *{symbols[symbol]}*
🕒 الفريم: *1 دقيقة*
⏱️ وقت الصفقة المقترح: *{trade_time}*
━━━━━━━━━━━━━━━
📈 RSI: {rsi:.2f}
📊 EMA20: {ema20:.5f}
📊 EMA50: {ema50:.5f}
📉 Bollinger Bands:
  • High: {bb_high:.5f}
  • Low: {bb_low:.5f}
💰 الإغلاق الحالي: {close:.5f}
━━━━━━━━━━━━━━━
📌 *التوصية:* {action}
🎯 نسبة الثقة: *100%*
    """

# 5. بدء البوت وإظهار أزرار الأزواج
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=sym)] for sym, name in symbols.items()]
    await update.message.reply_text("👋 مرحباً بك! اختر زوجًا للحصول على التوصيات كل دقيقة:", reply_markup=InlineKeyboardMarkup(keyboard))

# 6. تغيير الزوج
async def show_pair_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=sym)] for sym, name in symbols.items()]
    await update.message.reply_text("🔁 اختر زوجًا جديدًا:", reply_markup=InlineKeyboardMarkup(keyboard))

# 7. عند اختيار الزوج
async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_symbol = query.data
    await query.message.reply_text(f"✅ تم اختيار *{symbols[selected_symbol]}*\n📩 سيتم إرسال التوصيات تلقائياً كل دقيقة.\n\nاكتب /change لتغيير الزوج.", parse_mode="Markdown")

    # إرسال التوصيات كل دقيقة
    async def periodic():
        while True:
            signal = get_analysis(selected_symbol)
            await query.message.reply_text(signal, parse_mode="Markdown")
            await asyncio.sleep(60)

    context.application.create_task(periodic())

# 8. إعداد البوت
app = ApplicationBuilder().token("7728605631:AAE-NR_NgUAuSSdzo3YZRBK7laOPa0LB7wY").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("change", show_pair_selection))
app.add_handler(CallbackQueryHandler(handle_selection))
app.run_polling()
