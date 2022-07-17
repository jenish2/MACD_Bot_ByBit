import os, json
from bot import Bot

with open(os.path.join(os.path.dirname(__file__),"json_files",'credentials.json')) as f:
	credentials = json.load(f)
	f.close()

with open(os.path.join(os.path.dirname(__file__),"json_files",'settings.json')) as f:
	config = json.load(f)
	f.close()

bot = Bot(credentials,config)
bot.start()