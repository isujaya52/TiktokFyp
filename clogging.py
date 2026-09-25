import logging
import asyncio
from config import LOGS_ID,app
from pyrogram import Client

# ---------------------------------------------------------
# BATCHING LOG HANDLER (MENGGABUNGKAN LOG AGAR TIDAK SPAM)
# ---------------------------------------------------------
class BufferedTelegramLogHandler(logging.Handler):
    def __init__(self, client: Client, log_chat_id: int, flush_interval: int = 5):
        super().__init__()
        self.client = client
        self.log_chat_id = log_chat_id
        self.flush_interval = flush_interval
        self.log_queue = []
        self._lock = asyncio.Lock()
        self._task = None

    def emit(self, record):
        # Abaikan log peringatan FloodWait dari Pyrogram untuk mencegah siklus spam tak terbatas
        log_msg = str(record.getMessage())
        if "Waiting for" in log_msg and "seconds before continuing" in log_msg:
            return

        formatted_msg = self.format(record)
        self.log_queue.append(formatted_msg)

    async def start_worker(self):
        """Worker yang akan mengirimkan gabungan log secara berkala"""
        while True:
            await asyncio.sleep(self.flush_interval)
            if not self.log_queue:
                continue

            # Ambil semua log yang terkumpul
            logs_to_send = self.log_queue.copy()
            self.log_queue.clear()

            # Gabungkan pesan log menjadi satu string
            combined_text = "\n".join(logs_to_send)

            # Jika log gabungan terlalu panjang untuk 1 pesan Telegram (max 4096 karakter)
            chunks = []
            while len(combined_text) > 3800:
                # Potong per 3800 karakter
                split_pos = combined_text.rfind("\n", 0, 3800)
                if split_pos == -1:
                    split_pos = 3800
                chunks.append(combined_text[:split_pos])
                combined_text = combined_text[split_pos:].lstrip("\n")
            if combined_text:
                chunks.append(combined_text)

            # Kirim log dalam kelompok
            for chunk in chunks:
                try:
                    msg = f"📄 **SYSTEM LOGS BATCH**\n```text\n{chunk}\n```"
                    await self.client.send_message(chat_id=self.log_chat_id, text=msg)
                    await asyncio.sleep(1)  # Jeda 1 detik antar pengiriman chunk
                except Exception as e:
                    # Cetak error ke konsol lokal jika pengiriman log gagal
                    print(f"Gagal mengirim log ke Telegram: {e}")


# Setup Logging Basic
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

root_logger = logging.getLogger()

# Inisialisasi Handler Antrean Log (Flush setiap 5 detik)
tg_handler = BufferedTelegramLogHandler(app, LOGS_ID, flush_interval=5)
tg_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

root_logger.addHandler(tg_handler)
logger = logging.getLogger("config")