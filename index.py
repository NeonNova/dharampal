from flask import Flask
import threading
from dharampal_bot import bot

app = Flask(__name__)

@app.route('/')
def home():
    return "Dharampal Bot is running!"

def run_bot():
    bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=8080)