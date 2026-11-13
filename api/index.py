import os
import aiohttp
from fastapi import FastAPI, Request
from telegram import Bot, Update

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

app = FastAPI()
bot = Bot(token=TELEGRAM_TOKEN)


def get_weather_desc(code: int) -> tuple[str, str]:
    """Chuyển đổi mã thời tiết WMO sang mô tả tiếng Việt và icon."""
    if code == 0:
        return "☀️", "Trời quang đãng"
    elif code in (1, 2, 3):
        return "⛅", "Có mây rải rác"
    elif code in (45, 48):
        return "🌫️", "Có sương mù"
    elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "🌧️", "Có mưa"
    elif code in (71, 73, 75, 77, 85, 86):
        return "❄️", "Có tuyết rơi"
    elif code in (95, 96, 99):
        return "⛈️", "Có dông bão"
    return "🌤️", "Thời tiết ôn hòa"


async def get_weather_data(city: str) -> str:
    async with aiohttp.ClientSession() as session:
        # Bước 1: Tìm tọa độ (vĩ độ, kinh độ) từ tên thành phố
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": city, "count": 1, "language": "vi", "format": "json"}
        async with session.get(geo_url, params=geo_params) as geo_res:
            geo_data = await geo_res.json()

        if not geo_data.get("results"):
            return f"❌ Không tìm thấy thành phố **{city}**. Vui lòng kiểm tra lại chính tả (VD: `Hanoi`, `Ho Chi Minh`, `Tokyo`)."

        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        city_name = location["name"]
        country = location.get("country", "")

        # Bước 2: Lấy dữ liệu thời tiết hiện tại theo tọa độ
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
        }
        async with session.get(weather_url, params=weather_params) as w_res:
            if w_res.status != 200:
                return "⚠️ Dịch vụ thời tiết hiện đang gặp sự cố. Vui lòng thử lại sau."
            w_data = await w_res.json()

    current = w_data["current"]
    temp = current["temperature_2m"]
    feels_like = current["apparent_temperature"]
    humidity = current["relative_humidity_2m"]
    wind_speed = current["wind_speed_10m"]
    icon, description = get_weather_desc(current["weather_code"])

    return (
        f"{icon} **Thời tiết tại {city_name}, {country}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"• **Trạng thái:** {description}\n"
        f"• **Nhiệt độ:** {temp}°C (Cảm giác như {feels_like}°C)\n"
        f"• **Độ ẩm:** {humidity}%\n"
        f"• **Tốc độ gió:** {wind_speed} km/h"
    )


@app.get("/{full_path:path}")
async def health_check(full_path: str = ""):
    return {"status": "Bot is running on Vercel!"}


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
                "• Gõ trực tiếp tên thành phố (VD: `Hanoi`, `Da Nang`, `Tokyo`)\n"
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
