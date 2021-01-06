import asyncio

from discord.ext import commands
import discord

from setting import UserSetting
from cogs.utils.voice_util import VoiceFactory

class LoginTheme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(
            self, member: discord.Member,
            before: discord.VoiceState, after: discord.VoiceState):
        # botは無視
        if member.bot:
            return

        # 移動していない（ミュート状態の切り替えなど）なら無視
        if before.channel == after.channel:
            return

        # 退席なら無視
        if after.channel is None:
            return

        guild = self.bot.get_guild(member.guild.id)
        if guild is None:
            return None
        vc = guild.voice_client
        if vc is None:
            return

        # 音声ファイルを取得する
        vf = await self.__fetch_user_theme(member.id, member.guild.id)
        if vf is None:
            return

        for _ in range(600):
            try:
                vc.play(
                    discord.FFmpegPCMAudio(str(vf)),
                    after=lambda e: vf.unlink())
                break
            except discord.ClientException:
                await asyncio.sleep(0.2)
        else:
            vf.unlink()

    @commands.group(aliases=['th'])
    async def theme(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @theme.command()
    async def stop(self, ctx):
        # TODO: テーマ機能の一時停止
        pass

    @theme.command()
    async def resume(self, ctx):
        # TODO: テーマ機能の再開
        pass

    @theme.command(aliases=['ch'])
    async def change(self, ctx, url: str):
        # メンションが含まれていなければ、メッセージ送信者のidを入れる
        if len(ctx.message.mentions) > 0:
            user_id = ctx.message.mentions[0].id
        else:
            user_id = ctx.author.id

        # user_idを持ったユーザーがギルド内に存在するかチェックする
        member = ctx.message.guild.get_member(user_id)
        if member is None:
            return

        # メッセージ送信者がそれ以外の人の設定を変更しようとしている場合の権限チェック
        if user_id != ctx.author.id:
            if member.guild_permissions.manage_nicknames is False:
                return
        
        # 受け取ったURLが音声ファイルならテーマファイルとして設定する
        guild_id = ctx.message.guild.id
        data = UserSetting.get_setting(user_id)
        if "theme" in data:
            data["theme"][str(guild_id)] = url
        else:
            data["theme"] = {str(guild_id): url}
        UserSetting.update(user_id, data)

    def __get_user_theme(self, user_id: int, guild_id: int):
        data = UserSetting.get_setting(user_id)
        return data["theme"].get(str(guild_id), None)

    async def __fetch_user_theme(self, user_id: int, guild_id: int):
        data = self.__get_user_theme(user_id, guild_id)
        if data is None:
            return None
        return await VoiceFactory.create_voice_from_url(data)

def setup(bot):
    bot.add_cog(LoginTheme(bot))
