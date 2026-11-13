import os
import aiohttp
from fastapi import FastAPI, Request
from telegram import Bot, Update

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

app = FastAPI()
bot = Bot(token=TELEGRAM_TOKEN)


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
                return "⚠️ Dịch vụ thời tiết hiện đang gặp sự cố hoặc API Key chưa kích hoạt."
            data = await response.json()

    city_name = data["name"]
    country = data["sys"]["country"]
    temp = round(data["main"]["temp"], 1)
    feels_like = round(data["main"]["feels_like"], 1)
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]
    description = data["weather"][0]["description"].capitalize()

    return (
        f"🌤 **Thời tiết tại {city_name}, {country}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"• **Trạng thái:** {description}\n"
        f"• **Nhiệt độ:** {temp}°C (Cảm giác như {feels_like}°C)\n"
        f"• **Độ ẩm:** {humidity}%\n"
        f"• **Tốc độ gió:** {wind_speed} m/s"
    )


# Hứng mọi request GET (kiểm tra trạng thái)
@app.get("/{full_path:path}")
async def health_check(full_path: str = ""):
    return {"status": "Bot is running on Vercel!", "path": full_path}


# Hứng mọi request POST từ Telegram gửi tới (không bao giờ bị lệch 404)
@app.post("/{full_path:path}")
async def telegram_webhook(request: Request, full_path: str = ""):
    data = await request.json()
    update = Update.de_json(data, bot)

    if update.message and update.message.text:
        chat_id = update.message.chat_id
        text = update.message.text.strip()

        if text.startswith("/start") or text.startswith("/help"):
            reply = (
                "Xin chào! 👋 Tôi là Bot Dự Báo Thời Tiết.\n\n"
                "• Gõ trực tiếp tên thành phố (VD: `Hanoi`, `Tokyo`)\n"
                "• Hoặc dùng lệnh: `/thoitiet <tên thành phố>`"
            )
        elif text.startswith("/thoitiet"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                reply = "Vui lòng nhập tên thành phố. Ví dụ: `/thoitiet Da Nang`"
            else:
                reply = await get_weather_data(parts[1])
        else:
            reply = await get_weather_data(text)

        await bot.send_message(chat_id=chat_id, text=reply, parse_mode="Markdown")

    return {"ok": True}
