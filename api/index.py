import os
import aiohttp
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

app = FastAPI()

# Khởi tạo đối tượng Bot Application
ptb_app = Application.builder().token(TELEGRAM_TOKEN).build()


async def get_weather_data(city: str) -> str:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "vi",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 404:
                return f"❌ Không tìm thấy thành phố **{city}**. Vui lòng kiểm tra lại chính tả (thử gõ không dấu, ví dụ: `Hanoi`)."
            if response.status != 200:
                return "⚠️ Dịch vụ thời tiết hiện đang gặp sự cố. Vui lòng thử lại sau."
            data = await response.json()

    city_name = data["name"]
    country = data["sys"]["country"]
    temp = round(data["main"]["temp"], 1)
    feels_like = round(data["main"]["feels_like"], 1)
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]
    description = data["weather"][0]["description"].capitalize()

    weather_id = data["weather"][0]["id"]
    if 200 <= weather_id < 300:
        icon = "⛈️"
    elif 300 <= weather_id < 600:
        icon = "🌧️"
    elif 600 <= weather_id < 700:
        icon = "❄️"
    elif 700 <= weather_id < 800:
        icon = "🌫️"
    elif weather_id == 800:
        icon = "☀️"
    else:
        icon = "☁️"

    return (
        f"{icon} **Thời tiết tại {city_name}, {country}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"• **Trạng thái:** {description}\n"
        f"• **Nhiệt độ:** {temp}°C (Cảm giác như {feels_like}°C)\n"
        f"• **Độ ẩm:** {humidity}%\n"
        f"• **Tốc độ gió:** {wind_speed} m/s"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = (
        "Xin chào! 👋 Tôi là Bot Dự Báo Thời Tiết (chạy trên Vercel).\n\n"
        "**Cách sử dụng:**\n"
        "• Gõ trực tiếp tên thành phố (VD: `Hanoi`, `Tokyo`)\n"
        "• Hoặc dùng lệnh: `/thoitiet <tên thành phố>`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập tên thành phố. Ví dụ: `/thoitiet Da Nang`",
            parse_mode="Markdown",
        )
        return
    city = " ".join(context.args)
    report = await get_weather_data(city)
    await update.message.reply_text(report, parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text:
        city = update.message.text.strip()
        report = await get_weather_data(city)
        await update.message.reply_text(report, parse_mode="Markdown")


# Đăng ký handlers
ptb_app.add_handler(CommandHandler("start", start_command))
ptb_app.add_handler(CommandHandler("help", start_command))
ptb_app.add_handler(CommandHandler("thoitiet", weather_command))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


@app.get("/")
async def health_check():
    """Endpoint kiểm tra trạng thái server"""
    return {"status": "Bot is running on Vercel!"}


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Endpoint nhận tin nhắn từ Telegram"""
    data = await request.json()
    async with ptb_app:
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
    return {"ok": True}