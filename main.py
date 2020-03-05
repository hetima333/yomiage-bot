import os
import traceback

import discord
from discord.ext import commands
from pathlib import Path

from config import Config
import extentions

TOKEN = os.environ['DISCORD_BOT_TOKEN']


# Botクラス
class Lunalu(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=Config.get_global()["prefix"],
            fetch_offline_members=False
        )

        # 拡張機能の読み込み
        for extention in extentions.extentions:
            try:
                self.load_extension(f'cogs.{extention}')
            except Exception:
                traceback.print_exc()

    # 起動時のイベント
    async def on_ready(self):
        print(f'Ready: {self.user} (ID: {self.user.id})')
        activity = discord.Game(f'VC読み上げ')
        await self.change_presence(activity=activity)

    # Botを起動させる
    def run(self):
        super().run(TOKEN)


# Botの作成
bot = Lunalu()

# Botの起動
if __name__ == '__main__':
    bot.run()
