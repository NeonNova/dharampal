import os
from flask import Flask
from threading import Thread
from dharampal_bot import bot

app = Flask('')

@app.route('/')
def home():
    return "Dharampal Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv('DISCORD_TOKEN'))