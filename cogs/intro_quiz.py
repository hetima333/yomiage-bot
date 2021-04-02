import asyncio
import json
import random

from discord.ext import commands
import discord
import youtube_dl

from enum import Enum

from pathlib import Path
from pydub import AudioSegment
from pydub.utils import ratio_to_db

from config import Config


class QuizStatus(Enum):
    Idle = 0
    Downloading = 1
    Converting = 2
    Playing = 3


class IntroQuiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.INTRO_DATA_FILE = Path('../lunalu-bot/data/json/intro_data.json')

        self.trigger_emojis = ["🔁", "➡"]
        self.reply_message = None
        self.embed_message = None

        self.intro_list = list()
        self.pos = 0
        self.operation_embed = discord.Embed(
            color=Config.get_global()['embed_color'])
        self.operation_embed.add_field(
            name="操作方法",
            value="このメッセージにスタンプを押すことで操作できるわ。\n🔁でもう一度再生、➡で次の問題へ")

        self.current_status = QuizStatus.Idle

    @commands.group()
    async def intro(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @intro.command()
    async def start(self, ctx, *, arg: str = "all"):
        _arg = arg.replace(' ', '')

        # jsonからデータを読み込む
        with self.INTRO_DATA_FILE.open() as f:
            intro_data = json.loads(f.read())

        # 必要なデータだけを抽出する
        if _arg != "all":
            self.intro_list = [s for s in intro_data if _arg in s['tags']]
        else:
            self.intro_list = intro_data
        random.shuffle(self.intro_list)
        self.pos = 0

        self.reply_message = await ctx.message.reply(
            f"イントロクイズを開始するわ。（全{len(self.intro_list)}問）")
        # 操作バネルEmbedを送信する
        self.embed_message = await ctx.message.channel.send(
            embed=self.operation_embed)

        for item in self.trigger_emojis:
            await self.embed_message.add_reaction(item)

        await self.__download_music(self.intro_list[self.pos]["url"])
        await self.__play_intro(ctx.author.guild.id)

        # ステータスをアイドルにする
        self.current_status = QuizStatus.Idle
        await self.__update_embed_with_status(self.current_status)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # 待機中以外なら無視する
        if self.current_status != QuizStatus.Idle:
            return

        # クイズが開始されていなかったら無視する
        if self.embed_message is None:
            return

        emoji = str(payload.emoji)
        # 開始絵文字以外は無視
        if emoji not in self.trigger_emojis:
            return

        user = await self.bot.fetch_user(payload.user_id)
        # 絵文字をつけたユーザーがbotだった場合は無視
        if user.bot:
            return

        if payload.message_id != self.embed_message.id:
            return

        # ステータスをダウンロード中にする
        self.current_status = QuizStatus.Downloading
        await self.__update_embed_with_status(self.current_status)

        if emoji == "🔁":
            await self.__play_intro(self.reply_message)

        if emoji == "➡":
            if self.pos + 1 >= len(self.intro_list):
                await self.reply_message.edit(
                    content=f'問題は全て終了したわ。お疲れ様。\n{self.intro_list[self.pos]["url"]}')
            else:
                await self.reply_message.edit(
                    content=f'正解はこれよ。（{self.pos+1}/{len(self.intro_list)}問）\n{self.intro_list[self.pos]["url"]}')
                self.pos += 1
                await self.__download_music(self.intro_list[self.pos]["url"])
                await self.__play_intro(self.reply_message.guild.id)

        # ステータスをアイドルにする
        self.current_status = QuizStatus.Idle
        await self.__update_embed_with_status(self.current_status)

        member = self.reply_message.guild.get_member(payload.user_id)
        if member is not None:
            await self.reply_message.remove_reaction(emoji, member)

    async def __update_embed_with_status(self, status: QuizStatus):
        embed = self.operation_embed
        if status == QuizStatus.Idle:
            embed.set_footer(text="ステータス：待機中")
        if status == QuizStatus.Downloading:
            embed.set_footer(text="ステータス：ダウンロード中")
        if status == QuizStatus.Playing:
            embed.set_footer(text="ステータス：再生中")
        if status == QuizStatus.Converting:
            embed.set_footer(text="ステータス：音声ファイルの変換中")

        await self.embed_message.edit(embed=embed)

    async def __download_music(self, url: str):
        self.current_status = QuizStatus.Downloading
        await self.__update_embed_with_status(self.current_status)

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

        self.current_status = QuizStatus.Converting
        await self.__update_embed_with_status(self.current_status)

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
        self.current_status = QuizStatus.Playing
        await self.__update_embed_with_status(self.current_status)

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
