import asyncio
import json
import random

from discord.ext import commands
import discord
import youtube_dl

from pathlib import Path
from pydub import AudioSegment
from pydub.utils import ratio_to_db

from config import Config


class IntroQuiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.INTRO_DATA_FILE = Path('../lunalu-bot/data/json/intro_data.json')

        self.trigger_emojis = ["🔁", "➡"]
        self.message_id = 0

        self.intro_list = list()
        self.pos = 0
        self.operation = "**操作説明**\nこのメッセージにスタンプを押すことで操作できるわ。\n🔁でもう一度再生、➡で次の問題へ"

    @commands.group()
    async def intro(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @intro.command()
    async def start(self, ctx):
        message = await ctx.message.reply(f"イントロクイズを開始するわ。\n{self.operation}")
        self.message_id = message.id
        for item in self.trigger_emojis:
            await message.add_reaction(item)

        # jsonからデータを読み込む
        with self.INTRO_DATA_FILE.open() as f:
            intro_data = json.loads(f.read())
        # TODO: 必要なデータだけを抽出する
        self.intro_list = intro_data

        random.shuffle(self.intro_list)
        self.pos = 0

        await self.__download_music(self.intro_list[self.pos]["url"])
        await self.__play_intro(ctx.author.guild.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        emoji = str(payload.emoji)
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
            if self.pos + 1 >= len(self.intro_list):
                await message.edit(
                    content=f'問題は全て終了したわ。お疲れ様。\n{self.intro_list[self.pos]["url"]}\n{self.operation}')
            else:
                await message.edit(
                    content=f'正解はこれよ。\n{self.intro_list[self.pos]["url"]}\n{self.operation}')
                self.pos += 1
                await self.__download_music(self.intro_list[self.pos]["url"])
                await self.__play_intro(message.guild.id)

        member = message.guild.get_member(payload.user_id)
        if member is not None:
            await message.remove_reaction(emoji, member)

    async def __download_music(self, url: str):
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
        # 曲の先頭から無音部分が終わるまでの時間を取得
        start_trim = self.__detect_leading_silence(sound)
        # 無音部分終わりから5秒間を抽出
        sound = sound[start_trim:start_trim+5000]
        # 音量調整
        sound = sound + ratio_to_db(2100 / sound.rms)
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

    def __detect_leading_silence(self, sound, silence_threshold=-50.0, chunk_size=10):
        '''
        無音部分が終わるまでの長さを取得する
        '''
        trim_ms = 0  # ms

        assert chunk_size > 0  # to avoid infinite loop
        while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
            trim_ms += chunk_size

        return trim_ms


def setup(bot):
    bot.add_cog(IntroQuiz(bot))
