import asyncio
import os
import urllib.request
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import motor.motor_asyncio
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

# ==========================================
# 1. إعدادات المتغيرات
# ==========================================
API_ID = 26347457               
API_HASH = "46a1b4f0da186537f3164714b3dae9a4"     
BOT_TOKEN = "9086727497:AAEVYXwF6QbwpEIDt7VIUS_pQm_gU_vcz4w"   
MONGO_URL = "mongodb+srv://aseelothman_db_user:TnMnkGXN5HyBSWmj@cluster0.hw07bcg.mongodb.net/" 
WEBAPP_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://your-app-name.onrender.com")
ADMIN_ID = "8627317155"         

# ==========================================
# 2. إعداد قاعدة البيانات (MongoDB)
# ==========================================
client_db = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client_db.ArvexPayDB
users_collection = db.users

# ==========================================
# 3. إعداد السيرفر (FastAPI)
# ==========================================
app = FastAPI()
bot = None # سنقوم بتعريف البوت لاحقاً من داخل السيرفر لضمان التوافق

class UserData(BaseModel):
    tg_id: str
    added_balance: float = 0.0
    custom_address: str = ""
    withdraw_fee: float = 0.0
    swap_fee: float = 0.0
    req_deposit: float = 0.0
    has_deposited: bool = False

@app.get("/ping")
async def ping():
    return {"status": "alive"}

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

@app.get("/api/user/{tg_id}")
async def get_user(tg_id: str):
    user = await users_collection.find_one({"tg_id": tg_id})
    if user:
        user["_id"] = str(user["_id"])
        return user
    new_user = {"tg_id": tg_id, "added_balance": 0.0, "custom_address": "", "withdraw_fee": 0, "swap_fee": 0, "req_deposit": 0, "has_deposited": False}
    await users_collection.insert_one(new_user.copy())
    return new_user

@app.post("/api/admin/update_user")
async def update_user(data: UserData, admin_id: str):
    if str(admin_id) != str(ADMIN_ID):
        raise HTTPException(status_code=403, detail="Not Authorized")
    await users_collection.update_one({"tg_id": data.tg_id}, {"$set": data.dict()}, upsert=True)
    return {"status": "success"}

# ==========================================
# 4. تشغيل البوت بشكل متزامن مع السيرفر (الحل الجذري)
# ==========================================
@app.on_event("startup")
async def on_startup():
    global bot
    print("جاري تهيئة البوت داخل نفس مسار السيرفر...")
    
    # 1. حذف أي ارتباط قديم (Webhook) قد يمنع وصول الرسائل للبوت
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
    except:
        pass

    # 2. إنشاء البوت من داخل السيرفر لضمان التوافق التام (Event Loop)
    bot = Client("ArvexBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

    # 3. تعريف أوامر البوت
    @bot.on_message(filters.command("start"))
    async def start_cmd(client, message):
        keyboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton("🚀 فتح المحفظة (Web3)", web_app=WebAppInfo(url=WEBAPP_URL))],
                [KeyboardButton("🛡 حول المحفظة والأمان")]
            ],
            resize_keyboard=True
        )
        welcome_text = (
            "مرحباً بك في بوت ArvexPay Web3 Wallet! 💎⚡\n"
            "المحفظة المباشرة والآمنة لإدارة وتداول أصولك الرقمية\n"
            "عبر شبكات البلوكشين (BSC, Ethereum, Polygon)\n"
            "مباشرة من داخل تيليجرام."
        )
        await message.reply_text(welcome_text, reply_markup=keyboard)

    @bot.on_message(filters.regex("حول المحفظة والأمان"))
    async def security_info(client, message):
        info_text = (
            "حول المحفظة والأمان\n\n"
            "🛡 **الأمان والخصوصية في ArvexPay**\n"
            "• محفظة غير حضانية (Non-Custodial): مفاتيحك السرية (Private Keys) تُخزن وتُشفر على جهازك فقط، ولا يمتلك سيرفر البوت أي صلاحية للوصول لأموالك.\n"
            "• العبارة السرية (12 كلمة): هي وسيلتك الوحيدة لاسترجاع محفظتك، احفظها في مكان ورقي آمن ولا تشاركها مع أي شخص.\n"
            "• الشبكات المدعومة:\n"
            "* Binance Smart Chain (BNB)\n"
            "* Ethereum Mainnet (ETH)\n"
            "* Polygon Mainnet (MATIC)"
        )
        await message.reply_text(info_text)

    # 4. تشغيل البوت نهائياً
    await bot.start()
    print("✅ تم تشغيل البوت بنجاح وهو يستمع للرسائل!")

@app.on_event("shutdown")
async def on_shutdown():
    global bot
    if bot:
        await bot.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
