import json
import os
import asyncio
import feedparser
import yt_dlp
import requests
import time
from datetime import timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
from config import app,own
from clogging import logger
from BOT.decorators import bot_admin,admins_only,cmd_filter

JSON_FILE = "/home/container/tiktokbot/BOT/JSON/data.json"
BOT_START_TIME = time.time()

def get_uptime():
    """Mengembalikan durasi berjalan bot dalam bentuk string yang rapi"""
    uptime_seconds = int(time.time() - BOT_START_TIME)
    return str(timedelta(seconds=uptime_seconds))

# FUNGSI HELPER JSON & DOWNLOADER
def load_data():
    default_structure = {"fyp": {}, "following": {}, "chat_modes": {}, "total_sent_videos": 0}
    if not os.path.exists(JSON_FILE):
        save_data(default_structure)
        return default_structure
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "fyp" not in data:
                data["fyp"] = {}
            if "following" not in data:
                data["following"] = {}
            if "chat_modes" not in data:
                data["chat_modes"] = {}
            if "total_sent_videos" not in data:
                data["total_sent_videos"] = 0
            return data
    except json.JSONDecodeError:
        return default_structure


def save_data(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_latest_tiktok_video(username):
    """Mengecek metadata video terbaru dari profil TikTok menggunakan yt-dlp."""
    clean_user = username.replace("@", "")
    target_url = f"https://www.tiktok.com/@{clean_user}"
    
    ydl_opts = {
        'extract_flat': True,
        'playlistend': 1,
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                latest = info['entries'][0]
                video_id = latest.get('id')
                video_url = latest.get('url') or f"https://www.tiktok.com/@{clean_user}/video/{video_id}"
                title = latest.get('title', 'Video Baru TikTok')
                return video_id, video_url, title
    except Exception as e:
        logger.error(f"Error scraping {username}: {e}")
    
    return None, None, None       

def download_tiktok_video(video_url, output_filename):
    api_url = f"https://www.tikwm.com/api/?url={video_url}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        res = requests.get(api_url, headers=headers, timeout=15).json()
        if res.get("code") == 0:
            data = res.get("data", {})
            
            # 1. CEK APAKAH KONTEN BERISI SLIDE FOTO
            images = data.get("images")
            if images and isinstance(images, list) and len(images) > 0:
                photo_paths = []
                for idx, img_url in enumerate(images):
                    img_data = requests.get(img_url, headers=headers, timeout=15).content
                    img_filename = f"{output_filename}_img_{idx}.jpg"
                    with open(img_filename, "wb") as f:
                        f.write(img_data)
                    photo_paths.append(img_filename)
                return "photos", photo_paths

            # 2. JIKA BUKAN FOTO, UNDUH SEBAGAI VIDEO MP4
            direct_url = data.get("play") or data.get("wmplay")
            if direct_url:
                video_data = requests.get(direct_url, headers=headers, timeout=15).content
                video_filename = f"{output_filename}.mp4"
                with open(video_filename, "wb") as f:
                    f.write(video_data)
                return "video", video_filename

            logger.error("URL media tidak ditemukan di respon TikWM.")
            return None, None
        else:
            logger.error(f"TikWM Error: {res.get('msg')}")
            return None, None
    except Exception as e:
        logger.error(f"Gagal mendownload konten TikTok: {e}")
        return None, None

@app.on_message(filters.command("start"))
@bot_admin
@cmd_filter
async def start_cmd(client: Client, message: Message):
    text = (
        "🎬 **YoiTikTok Bot**\n\n"
        "⚙️ **PILIH MODE UNTUK CHAT INI:**\n"
        "• /fyp - Mode FYP (Hanya menerima pembaruan dari FYP Global Owner)\n"
        "• /jf - Mode Just Following (Hanya menerima pembaruan akun pilihan kalian)\n"
        "• /off - Matikan pembaruan video untuk chat ini\n\n"
        "📌 **MODE JUST FOLLOWING:**\n"
        "/follow <user> - Follow akun TikTok untuk chat ini\n"
        "/unfollow <user> - Unfollow akun TikTok\n"
        "/list - Lihat daftar akun TikTok yang di-follow di chat ini\n\n"
        "🔥 **MODE FYP (Khusus Owner Bot):**\n"
        "/addfyp <user> - Tambah akun ke FYP Global\n"
        "/delfyp <user> - Hapus akun dari FYP Global\n"
        "/listfyp - Lihat daftar FYP Global"
    )
    await message.reply_text(text)

    
@app.on_message(filters.command("ping"))
async def ping_cmd(client: Client, message: Message):
    start_time = time.time()
    msg = await message.reply_text("🏓 **Pinging...**")
    end_time = time.time()
    
    latency = round((end_time - start_time) * 1000, 2)
    uptime_str = get_uptime()
    
    await msg.edit_text(
        f"🏓 **Pong!**\n"
        f"⚡ **Latency:** `{latency} ms`\n"
        f"⏱ **Uptime:** `{uptime_str}`"
    )   
    
    
@app.on_message(filters.command("fyp"))
@bot_admin
@admins_only
async def set_mode_fyp(client: Client, message: Message):
    chat_id = str(message.chat.id)
    data = load_data()
    data["chat_modes"][chat_id] = "fyp"
    save_data(data)
    await message.reply_text("🔥 **Mode Diubah ke: FYP Global Mode**\nChat ini hanya akan menerima pembaruan dari daftar akun FYP Global.")


@app.on_message(filters.command("jf"))
@bot_admin
@admins_only
async def set_mode_jf(client: Client, message: Message):
    chat_id = str(message.chat.id)
    data = load_data()
    data["chat_modes"][chat_id] = "jf"
    save_data(data)
    await message.reply_text("📌 **Mode Diubah ke: Just Following Mode**\nChat ini hanya akan menerima pembaruan dari akun yang di-follow via `/follow`.")

@app.on_message(filters.command("off"))
@bot_admin
@admins_only
async def set_mode_off(client: Client, message: Message):
    chat_id = str(message.chat.id)
    data = load_data()
    data["chat_modes"][chat_id] = "off"
    save_data(data)
    await message.reply_text("🔕 **Mode Chat Di-nonaktifkan (OFF)**\nBot tidak akan mengirimkan pembaruan video TikTok ke chat ini sampai kamu mengaktifkannya kembali via `/fyp` atau `/jf`.")    
    
    
@app.on_message(filters.command("follow"))
@bot_admin
@admins_only
async def follow_cmd(client: Client, message: Message):
    chat_id = str(message.chat.id)
    data = load_data()

    # Cek apakah mode sudah diatur
    if chat_id not in data.get("chat_modes", {}):
        await message.reply_text("⚠️ **Mode belum diatur!**\nSilakan pilih mode chat terlebih dahulu menggunakan perintah:\n\n• /fyp - Mode FYP Global\n• /jf - Mode Just Following")
        return

    # Cek apakah sedang berada di mode JF
    if data["chat_modes"][chat_id] == "fyp":
        await message.reply_text("⚠️ Chat ini sedang berada di **Mode FYP**.\nUbah ke Mode Just Following dengan `/jf` untuk menggunakan fitur follow.")
        return
    
    if data["chat_modes"][chat_id] == "off":
        await message.reply_text("⚠️ **Mode chat nonaktif atau belum diatur!**\nSilakan aktifkan mode chat terlebih dahulu:\n\n• /fyp - Mode FYP Global\n• /jf - Mode Just Following")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Format: `/follow @username`")
        return

    raw_user = message.command[1].strip()
    username = raw_user if raw_user.startswith("@") else f"@{raw_user}"

    msg = await message.reply_text(f"🔍 Memeriksa **{username}**...")
    loop = asyncio.get_event_loop()
    video_id, _, _ = await loop.run_in_executor(None, get_latest_tiktok_video, username)

    if not video_id:
        await msg.edit_text(f"❌ Akun **{username}** tidak ditemukan.")
        return

    if chat_id not in data["following"]:
        data["following"][chat_id] = {}

    data["following"][chat_id][username] = video_id
    save_data(data)
    await msg.edit_text(f"✅ Berhasil mengikuti **{username}** di chat ini!")
  
    
@app.on_message(filters.command("unfollow"))
@bot_admin
@admins_only
async def unfollow_cmd(client: Client, message: Message):
    chat_id = str(message.chat.id)
    data = load_data()

    if chat_id not in data.get("chat_modes", {}):
        await message.reply_text("⚠️ **Mode belum diatur!** Silakan pilih mode chat lebih dulu dengan `/fyp` atau `/jf`.")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Format: `/unfollow @username`")
        return

    raw_user = message.command[1].strip()
    username = raw_user if raw_user.startswith("@") else f"@{raw_user}"

    if chat_id in data["following"] and username in data["following"][chat_id]:
        del data["following"][chat_id][username]
        save_data(data)
        await message.reply_text(f"🗑 Berhasil unfollow **{username}**.")
    else:
        await message.reply_text("❌ Akun tidak ditemukan di daftar chat ini.")


@app.on_message(filters.command("list"))
@bot_admin
@admins_only
async def list_cmd(client: Client, message: Message):
    chat_id = str(message.chat.id)
    data = load_data()

    if chat_id not in data.get("chat_modes", {}):
        await message.reply_text("⚠️ **Mode belum diatur!** Silakan pilih mode chat lebih dulu dengan `/fyp` atau `/jf`.")
        return

    if chat_id not in data["following"] or not data["following"][chat_id]:
        await message.reply_text("📭 Belum ada akun yang diikuti di chat ini.")
        return

    text = "📋 **Daftar Follow Chat Ini:**\n\n"
    for idx, (username, last_id) in enumerate(data["following"][chat_id].items(), 1):
        text += f"{idx}. **{username}** (`{last_id}`)\n"
    await message.reply_text(text)

    
@app.on_message(filters.command("addfyp"))
async def add_fyp_cmd(client: Client, message: Message):
    if message.from_user.id not in own:
        await message.reply_text("⛔ Perintah ini khusus untuk Owner Bot!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Format: `/addfyp @username`")
        return

    raw_user = message.command[1].strip()
    username = raw_user if raw_user.startswith("@") else f"@{raw_user}"

    msg = await message.reply_text(f"🔍 Menambahkan **{username}** ke FYP Global...")
    loop = asyncio.get_event_loop()
    video_id, _, _ = await loop.run_in_executor(None, get_latest_tiktok_video, username)

    if not video_id:
        await msg.edit_text(f"❌ Akun **{username}** tidak ditemukan.")
        return

    data = load_data()
    data["fyp"][username] = video_id
    save_data(data)
    await msg.edit_text(f"🔥 **{username}** berhasil masuk daftar FYP Global!")
    
@app.on_message(filters.command("delfyp"))
async def del_fyp_cmd(client: Client, message: Message):
    if message.from_user.id not in own:
        await message.reply_text("⛔ Perintah ini khusus untuk Owner Bot!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Format: `/delfyp @username`")
        return

    raw_user = message.command[1].strip()
    username = raw_user if raw_user.startswith("@") else f"@{raw_user}"
    data = load_data()

    if username in data["fyp"]:
        del data["fyp"][username]
        save_data(data)
        await message.reply_text(f"🗑 **{username}** dihapus dari FYP Global.")
    else:
        await message.reply_text("❌ Akun tidak ada di daftar FYP.")
    
@app.on_message(filters.command("listfyp"))
async def list_fyp_cmd(client: Client, message: Message):
    if message.from_user.id not in own:
        await message.reply_text("⛔ Perintah ini khusus untuk Owner Bot!")
        return
    data = load_data()
    if not data["fyp"]:
        await message.reply_text("📭 Daftar FYP Global masih kosong.")
        return

    text = "🔥 **Daftar Akun FYP Global:**\n\n"
    for idx, username in enumerate(data["fyp"].keys(), 1):
        text += f"{idx}. **{username}**\n"
    await message.reply_text(text)
    

@app.on_message(filters.command("stats"))
async def stats_cmd(client: Client, message: Message):
    data = load_data()
    chat_modes = data.get("chat_modes", {})
    
    total_chats = len(chat_modes)
    mode_fyp = sum(1 for m in chat_modes.values() if m == "fyp")
    mode_jf = sum(1 for m in chat_modes.values() if m == "jf")
    mode_off = sum(1 for m in chat_modes.values() if m == "off")

    # Hitung total akun unik yang diikuti di seluruh chat
    all_followed = set()
    for users in data.get("following", {}).values():
        all_followed.update(users.keys())

    total_fyp_accounts = len(data.get("fyp", {}))
    total_sent = data.get("total_sent_videos", 0)

    text = (
        "📊 **STATISTIK YOITIKTOK BOT**\n\n"
        f"💬 **Total Chat Terdaftar:** `{total_chats}`\n"
        f"├ 🔥 Mode FYP: `{mode_fyp}`\n"
        f"├ 📌 Mode Just Following: `{mode_jf}`\n"
        f"└ 🔕 Mode Off: `{mode_off}`\n\n"
        f"👥 **Total Akun Di-follow:** `{len(all_followed)}` akun\n"
        f"🔥 **Total Akun FYP Global:** `{total_fyp_accounts}` akun\n"
        f"🎬 **Total Video Terkirim:** `{total_sent}` video\n\n"
        f"⏱ **Uptime:** `{get_uptime()}`"
    )
    await message.reply_text(text)    
    
    
@app.on_message(filters.command("check"))
@bot_admin
@admins_only
async def manual_check(client: Client, message: Message):
    msg = await message.reply_text("🔄 Memeriksa & mengunduh pembaruan video...")
    await check_tiktok_updates()
    await msg.edit_text("✅ Pengecekan selesai.")


async def check_tiktok_updates():
    data = load_data()
    updated = False
    loop = asyncio.get_event_loop()

    chat_modes = data.get("chat_modes", {})

    # 1. CEK UPDATES MODE FOLLOWING
    for chat_id, users in data.get("following", {}).items():
        if chat_modes.get(chat_id) != "jf":
            continue

        for username, last_id in list(users.items()):
            try:
                v_id, v_url, title = await loop.run_in_executor(None, get_latest_tiktok_video, username)
                if v_id and v_id != last_id:
                    prefix = f"temp_flw_{chat_id}_{v_id}"
                    
                    content_type, downloaded_paths = await loop.run_in_executor(
                        None, download_tiktok_video, v_url, prefix
                    )

                    if content_type and downloaded_paths:
                        caption = (
                            f"📌 **[FOLLOWING] Konten Baru!** ✌︎㋡\n\n"
                            f"👤 **{username}**\n"
                            f"📝 {title}\n"
                            f"🔗 [TikTok]({v_url})"
                        )
                        
                        await send_tiktok_media(int(chat_id), content_type, downloaded_paths, caption)

                        data["following"][chat_id][username] = v_id
                        data["total_sent_videos"] = data.get("total_sent_videos", 0) + 1
                        updated = True

            except Exception as e:
                logger.error(f"Error Following {username}: {e}")

    # 2. CEK UPDATES MODE FYP
    fyp_chats = [cid for cid, m in chat_modes.items() if m == "fyp"]

    if fyp_chats:
        for username, last_id in list(data.get("fyp", {}).items()):
            try:
                v_id, v_url, title = await loop.run_in_executor(None, get_latest_tiktok_video, username)
                if v_id and v_id != last_id:
                    prefix = f"temp_fyp_{v_id}"
                    
                    content_type, downloaded_paths = await loop.run_in_executor(
                        None, download_tiktok_video, v_url, prefix
                    )

                    if content_type and downloaded_paths:
                        caption = (
                            f"🔥 **[FYP] Konten Terbaru!** ✌︎㋡\n\n"
                            f"👤 **{username}**\n"
                            f"📝 {title}\n"
                            f"🔗 [TikTok]({v_url})"
                        )

                        for target_chat in fyp_chats:
                            try:
                                await send_tiktok_media(int(target_chat), content_type, downloaded_paths, caption)
                                data["total_sent_videos"] = data.get("total_sent_videos", 0) + 1
                            except Exception as send_err:
                                logger.error(f"Gagal kirim FYP ke {target_chat}: {send_err}")

                        if content_type == "video" and os.path.exists(downloaded_paths):
                            os.remove(downloaded_paths)
                        elif content_type == "photos":
                            for p_path in downloaded_paths:
                                if os.path.exists(p_path):
                                    os.remove(p_path)

                    data["fyp"][username] = v_id
                    updated = True

            except Exception as e:
                logger.error(f"Error FYP {username}: {e}")

    if updated:
        save_data(data)               
                                 

async def send_tiktok_media(chat_id: int, content_type: str, paths, caption: str):
    """Mengirim video atau album foto ke Telegram lalu menghapus file temporer."""
    try:
        if content_type == "video":
            await app.send_video(chat_id=chat_id, video=paths, caption=caption)
            #if os.path.exists(paths):
               # os.remove(paths)
                
        elif content_type == "photos":
            # Telegram membatasi maksimal 10 foto per album / media group
            media_group = []
            for idx, p_path in enumerate(paths[:10]):
                if idx == 0:
                    # Menempelkan caption pada foto pertama
                    media_group.append(InputMediaPhoto(media=p_path, caption=caption))
                else:
                    media_group.append(InputMediaPhoto(media=p_path))
            
            await app.send_media_group(chat_id=chat_id, media=media_group)
            
            # Hapus seluruh file foto temporer
           # for p_path in paths:
               # if os.path.exists(p_path):
                  #  os.remove(p_path)

    except Exception as e:
        logger.error(f"Gagal mengirim media ke {chat_id}: {e}")
        # Bersihkan file jika terjadi error saat pengiriman
        if content_type == "video" and isinstance(paths, str) and os.path.exists(paths):
            os.remove(paths)
        elif content_type == "photos" and isinstance(paths, list):
            for p_path in paths:
                if os.path.exists(p_path):
                    os.remove(p_path)        


                

                    


     
