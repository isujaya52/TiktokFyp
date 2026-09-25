from config import app, own
from functools import wraps
from config import LOGS_ID
import os
import traceback
 

def admins_only(func):
  @wraps(func)
  async def admins(client,message,*args,**kwargs): 
    if message.from_user.id in own:
      return await func(client, message, *args, **kwargs)
    if message.chat.type.value == 'private':
      return await func(client,message,*args,**kwargs) 
    else:
      admin = await app.get_chat_member(message.chat.id,message.from_user.id)
      if admin.status.value in ['owner','administrator']:
        return await func(client, message, *args, **kwargs)
      else:
        return await message.reply_text("Anda harus menjadi admin untuk melakukan ini.")
  return admins


def bot_admin(func):
  @wraps(func)
  async def admins(client,message,*args,**kwargs):
    imbot = await app.get_me()
    idbot = imbot.id
    if message.from_user.id in own:
      return await func(client,message,*args,**kwargs)
    if message.chat.type.value == 'private':
      return await func(client,message,*args,**kwargs) 
    else:
      infobot = await app.get_chat_member(message.chat.id,idbot)
      if infobot.status.value in ['owner','administrator']:
        return await func(client,message,*args,**kwargs)
      else:
        return await message.reply_text("Saya harus menjadi admin untuk menjalankan perintah ini.")
  return admins




def cmd_filter(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        bot_info = await app.get_me()
        bot_username = bot_info.username
        
        text = message.text.split()[0] if message.text else ""
        
        if "@" in text and f"@{bot_username}" not in text:
            return 
            
        return await func(client, message, *args, **kwargs)
    return wrapper


