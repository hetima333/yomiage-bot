import asyncio
import random

from discord.ext import commands
import discord

import youtube_dl
from pydub import AudioSegment

class IntroQuiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trigger_emojis = ["🔁", "➡"]
        self.message_id = 0
        self.url_list = [
            "https://www.youtube.com/watch?v=cm-l2h6GB8Q",
            "https://www.youtube.com/watch?v=FDaj3N8yWps"
        ]
        self.random_order = []
        self.pos = 0

    @commands.group()
    async def intro(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @intro.command()
    async def start(self, ctx):
        message = await ctx.message.reply("イントロクイズを開始するわ")
        self.message_id = message.id
        for item in self.trigger_emojis:
            await message.add_reaction(item)

        self.random_order = list(range(len(self.url_list)))
        random.shuffle(self.random_order)
        self.pos = 0

        await self.__download_music(self.url_list[self.random_order[self.pos]])
        await self.__play_intro(ctx.author.guild.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        emoji = str(payload.emoji)
        print(emoji)
        # 開始絵文字以外は無視
        if emoji not in self.trigger_emojis:
            return

        user = await self.bot.fetch_user(payload.user_id)
        # 絵文字をつけたユーザーがbotだった場合は無視
        if user.bot:
            return

        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if message.id != self.message_id:
            return

        if emoji == "🔁":
            await self.__play_intro(message.guild.id)

        if emoji == "➡":
            if self.pos + 1>= len(self.url_list):
                await message.edit(content=f"問題は全て終了したわ。お疲れ様。\n{self.url_list[self.random_order[self.pos]]}")
            else:
                await message.edit(content=f"正解はこれよ。\n{self.url_list[self.random_order[self.pos]]}")
                self.pos += 1
                await self.__download_music(self.url_list[self.random_order[self.pos]])
                await self.__play_intro(message.guild.id)

        member = message.guild.get_member(payload.user_id)
        if member is not None:
            await message.remove_reaction(emoji, member)

    async def __download_music(self, url:str):
        # ダウンロード設定
        ydl = youtube_dl.YoutubeDL({
            'format': 'bestaudio/best',
            'outtmpl': 'data/input.%(ext)s',
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]
        })

        # 音楽ファイルのダウンロード
        with ydl:
            result = ydl.extract_info(
                url,
                download=True
            )

        # 音声ファイルの読み込み
        sound = AudioSegment.from_file("data/input.mp3", "mp3")
        # 0~5秒を抽出
        sound = sound[0:5000]
        # フェードイン（0.5秒）、フェードアウト（0.5秒）
        sound = sound.fade_in(500).fade_out(500)
        # 保存
        sound.export("data/output.mp3", format="mp3")

    async def __play_intro(self, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return None
        vc = guild.voice_client
        if vc is None:
            return

        for _ in range(600):
            try:
                vc.play(discord.FFmpegPCMAudio("data/output.mp3"))
                break
            except discord.ClientException:
                await asyncio.sleep(0.2)
        else:
            pass

def setup(bot):
    bot.add_cog(IntroQuiz(bot))
