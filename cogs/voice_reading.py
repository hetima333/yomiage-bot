import asyncio
import json
import re
from pathlib import Path

import discord
import emoji
from discord.ext import commands

from cogs.utils.msg_util import MessageConverter
from cogs.utils.voice_util import VoiceFactory
from cogs.utils.math_util import MathUtility
from config import Config
from setting import GuildSetting, UserSetting


class VoiceReading(commands.Cog, name='VC読み上げ'):
    def __init__(self, bot):
        self.bot = bot
        self.target_channel = None
        self.voice_client = None
        # 読み上げる文字数
        self.read_char_cnt = 50

        self.words_file = Path('../lunalu-bot/data/json/words.json')
        if self.words_file.exists() is False:
            with self.words_file.open('w') as f:
                f.write(r'{}')
        with self.words_file.open() as f:
            self.words = json.loads(f.read())

        self.sefifs_file = Path('./data/json/serifs.json')
        with self.sefifs_file.open() as f:
            self.serifs = json.loads(f.read())

    async def __leave_voice_channel(self):
        # VoiceClientが空なら処理しない
        if self.voice_client is None:
            return

        # VCに接続していたら切断する
        if self.voice_client.is_connected():
            await self.voice_client.disconnect()
        self.voice_client = None

        await self.target_channel.send(self.get_serif("leave_voice_channel"))
        self.target_channel = None

    def _convert_message(
            self, msg: str, max_length=0) -> str:
        _msg = msg
        # 正規表現置換
        _msg = MessageConverter.replace_by_re(_msg)
        self._load_words()
        # ユーザー辞書変換
        for (pre, post) in self.words.items():
            # _pre = pre.lower()
            if pre in _msg:
                _msg = _msg.replace(pre, post)
        _msg = emoji.demojize(_msg)
        # 英語かな変換
        _msg = MessageConverter.replace_eng_to_kana(_msg)
        # ローマ字かな変換
        _msg = MessageConverter.replace_roman_to_kana(_msg)

        # 長い文章はカットする
        if max_length != 0:
            if len(_msg) > max_length:
                _msg = _msg[:max_length] + '以下略'

        return _msg

    def _update_word(self) -> None:
        '''単語の更新'''
        _list = sorted(self.words.items(),
                       key=lambda x: len(x[0]), reverse=True)
        d = {}
        for k, v in _list:
            d[k] = v
        self.words = d
        with self.words_file.open('w') as f:
            f.write(json.dumps(self.words, ensure_ascii=False, indent=4))

    def _load_words(self) -> None:
        with self.words_file.open() as f:
            self.words = json.loads(f.read())

    def _set_status(self, user_id, status: str, param) -> None:
        '''ユーザー設定にパラメータを設定'''
        setting = UserSetting.get_setting(user_id)
        setting[status] = param
        UserSetting.update(user_id, setting)

    async def _update_status_and_send_msg(
            self, ctx: commands.Context,
            status: str, status_ja: str, param) -> None:
        '''ユーザー設定のパラメータ設定とメッセージ送信'''
        user_id = str(ctx.author.id)
        mention = ctx.author.mention
        before = UserSetting.get_setting(user_id)[status]
        self._set_status(user_id, status, param)
        await ctx.channel.send(
            content=self.get_serif(
                "status_change", mention, status_ja, before, param
            )
        )

    async def _show_user_setting(self, msg: discord.Message) -> None:
        '''ユーザー設定の表示'''
        user_id = str(msg.author.id)
        setting = UserSetting.get_setting(user_id)
        # Embedの作成
        embed = discord.Embed(color=Config.get_global()['embed_color'])
        embed.set_author(
            name=f'{msg.author.display_name} のボイス読み上げ設定',
            icon_url=msg.author.avatar_url
        )
        status_list = [
            f'声の種類　　　　： {setting["voice"]}',
            f'話す速度　　　　： {setting["speed"]}',
            f'トーン　　　　　： {setting["tone"]}',
            f'イントネーション： {setting["intone"]}'
        ]
        embed.add_field(name='ユーザー設定', value='\n'.join(status_list))

        await msg.channel.send(
            content=self.get_serif("show_user_status", msg.author.mention),
            embed=embed
        )

    # ====== ユーザー設定関数群 ======
    @commands.group(aliases=['vo'])
    async def voice(self, ctx):
        '''読み上げ音声に関する設定を行えるわ'''
        if ctx.invoked_subcommand is None:
            await ctx.channel.send(f'コマンドが間違っているわ…\n例えば、声のトーンを変更したい時は\n`{config.COMMAND_PREFIX}voice tone -20~20の数値` と入力してみて')

    @voice.command()
    async def status(self, ctx):
        '''ボイス設定状況を表示するわ'''
        await self._show_user_setting(ctx.message)

    @voice.command(aliases=['ch'])
    async def change(self, ctx, name: str):
        '''
        読み上げボイスの種類を変更するわ
        変更できるボイスは以下のとおりよ。
        ・normal
        ・happy
        ・bashful
        ・angry
        ・sad
        ・male
        ・miku
        '''
        if name not in VoiceFactory.get_voice_list():
            await ctx.channel.send(self.get_serif('voice_not_exist', ctx.author.mention))
            return
        await self._update_status_and_send_msg(
            ctx, 'voice', 'ボイスの種類', name
        )

    @voice.command(aliases=['spd'])
    async def speed(self, ctx, param: float):
        '''読み上げ速度を変更するわ'''
        _param = MathUtility.clamp(param, 0.0, 100.0)
        await self._update_status_and_send_msg(
            ctx, 'speed', '話す速度', _param
        )

    @voice.command()
    async def tone(self, ctx, param: float):
        '''声のトーンを変更するわ'''
        _param = MathUtility.clamp(param, 0.0, 100.0)
        await self._update_status_and_send_msg(
            ctx, 'tone', '声のトーン', _param
        )

    @voice.command()
    async def intone(self, ctx, param: float):
        '''イントネーションを変更するわ'''
        _param = MathUtility.clamp(param, 0.0, 100.0)
        await self._update_status_and_send_msg(
            ctx, 'intone', '声のイントネーション', _param
        )

    # @voice.command(aliases=['vol'])
    # async def volume(self, ctx, param: float):
    #     '''読み上げ音量を変更するわ(※現在使用できません)'''
    #     _param = MathUtility.clamp(param, 0.0, 100.0)
    #     await self._update_status_and_send_msg(
    #         ctx, 'volume', '声の大きさ', _param
    #     )

    @commands.command(aliases=['aj'])
    async def auto_join(self, ctx):
        '''VCに接続した時に自動的に私を呼ぶことができるわ'''
        voice_state = ctx.author.voice
        if voice_state is None:
            await ctx.channel.send('auto_join：VCに接続していないと設定できないメッセージを追加する')
            return

        if voice_state.channel is None:
            await ctx.channel.send('auto_join：VCが上手く取得できないので再接続を促すメッセージを追加する')
            return

        conf = GuildSetting.get_setting(ctx.guild.id)
        watch_channel_id = conf['watch_channel_id']

        _flg = watch_channel_id['voice'] == 0
        if _flg:
            watch_channel_id['voice'] = voice_state.channel.id
            watch_channel_id['text'] = ctx.channel.id
        else:
            watch_channel_id['voice'] = 0
            watch_channel_id['text'] = 0

        GuildSetting.update_setting(ctx.guild.id, conf)

        msg = f'{ctx.author.mention} '
        msg += self.get_serif('auto_join_enable', voice_state.channel.name,
                              ctx.channel.mention) if _flg else self.get_serif('auto_join_disable')
        await ctx.channel.send(msg)

    # ====== 動作関数群 ======
    async def __join(
            self,
            text_channel: discord.TextChannel,
            voice_channel: discord.VoiceChannel) -> None:
        # VoiceClientが空またはVCに未接続なら接続
        if self.voice_client is None:
            self.voice_client = await voice_channel.connect()
        if self.voice_client.is_connected() is False:
            await self.voice_client.connect(timeout=3000, reconnect=False)

        if self.target_channel is None or\
                self.target_channel.id != text_channel.id:
            await text_channel.send(
                self.get_serif('start_reading', text_channel.mention))
            self.target_channel = text_channel
        # else:
        #     await text_channel.send(
        #         self.get_serif('already_reading', text_channel.mention))

    @commands.command()
    async def join(self, ctx):
        '''VCに私を呼ぶことができるわ'''
        if ctx.author.voice is None:
            await ctx.channel.send('私を呼ぶ時はVCに入った状態で呼んで')
        else:
            await self.__join(ctx.channel, ctx.author.voice.channel)

    @commands.command(aliases=['exit'])
    async def bye(self, ctx):
        '''VCから私を切断することができるわ'''
        # VoiceClientが空またはVCに未接続ならエラーメッセージ
        if self.voice_client is None:
            return

        if self.voice_client.is_connected() is False:
            await ctx.channel.send(f"VCにいないわ…\n私をVCに呼びたいときは`{Config.get_prefix()}join`と入力して")
            return

        await ctx.message.add_reaction('👋')
        await self.__leave_voice_channel()

    @commands.command(aliases=['st'])
    async def stop(self, ctx):
        '''読み上げ中の音声を停止するわ'''
        # 参加中のVCがなければメッセージを返す
        if self.voice_client is None or\
                self.voice_client.is_connected() is False:
            await ctx.channel.send('何も喋ってないわ。作業に集中しましょ')
            return

        # 再生中なら止める
        if self.voice_client.is_playing():
            await ctx.message.add_reaction('⏹')
            self.voice_client.stop()

    @commands.command(usage='読みを追加したい単語 読み', aliases=['word_add'])
    async def wa(self, ctx, *args) -> None:
        '''
        単語の読みを登録することができるわ
        -wa 単語 読み の形式で登録できるわ
        '''
        if len(args) == 2:
            de_custom_emoji = re.compile(r"<:(\w+):\d+>")
            word = de_custom_emoji.sub(r'\1', args[0])
            read = de_custom_emoji.sub(r'\1', args[1])
            self.words[word] = read
            self._update_word()
            await ctx.channel.send(
                self.get_serif('complete_word_add', args[0], read))
        else:
            await ctx.channel.send(
                self.get_serif('error_word_add', ctx.prefix))
            return

    @commands.command(usage='読みを削除したい単語', aliases=['word_delete'])
    async def wd(self, ctx, *args) -> None:
        '''
        単語の読みを削除することができるわ
        -wd 単語 の形式で削除できるわ
        '''
        if len(args) == 1:
            de_custom_emoji = re.compile(r"<:(\w+):\d+>")
            word = de_custom_emoji.sub(r'\1', args[0])
            del self.words[word]
            self._update_word()
            await ctx.channel.send(
                self.get_serif('complete_word_delete', args[0]))
        else:
            await ctx.channel.send(
                self.get_serif('error_word_delete', ctx.prefix))
            return

    @commands.command(aliases=['word_list'])
    async def wl(self, ctx) -> None:
        '''登録されている単語の読み一覧を表示するわ'''
        word_list = [f"{self.get_serif('show_word_list')}\n単語（読み）"]
        self._load_words()
        for (word, read) in self.words.items():
            word_list.append(f'・{word}（{read}）')
        await ctx.channel.send('\n'.join(word_list))

    @commands.command(aliases=['sound_list'])
    async def sl(self, ctx) -> None:
        '''登録されているサウンド一覧を表示するわ'''
        msg = "音源はこのスプレッドシートに記載されているわ\nhttps://docs.google.com/spreadsheets/d/1_P_o1PGRqv_8Wdcpqj_Nd9rd-cRohsolUMuENbAxVi8/edit?usp=sharing"
        await ctx.channel.send(msg)

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

        if self.voice_client is not None:
            # VCに接続済みの場合の動作
            if self.voice_client.is_connected():
                # 関係のないサーバーは無視
                if member.guild != self.target_channel.guild:
                    return
                # 参加者がbotのみになったら退出
                if len([1 for user in self.voice_client.channel.members if not user.bot]) < 1:
                    await self.__leave_voice_channel()

        # VCに未接続の場合の動作
        else:
            # 接続チャンネルがなければ無視
            if after.channel is None:
                return

            conf = GuildSetting.get_setting(member.guild.id)
            watch_channel_id = conf['watch_channel_id']

            # 接続したチャンネルが購読チャンネルでなければ処理をしない
            if after.channel.id != watch_channel_id['voice']:
                return

            # 自動参加チャンネルIDが設定されていたら接続する
            channel_id = watch_channel_id['text']
            if channel_id != 0:
                try:
                    _target_channel = await self.bot.fetch_channel(channel_id)
                    # ※暫定対策のため、後ほど削除
                    # 読み上げ対象のチャンネルが対象のサーバーでない場合は無視
                    if _target_channel.guild != member.guild:
                        return
                except Exception:
                    # TODO: auto_join設定者に対して再設定をうながす通知
                    return
                else:
                    # VCに接続
                    await self.__join(_target_channel, after.channel)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # コマンドは読み上げない
        if message.content.startswith(Config.get_prefix()):
            return

        # botの発言は読み上げない
        if message.author.bot:
            return

        if self.target_channel is None:
            conf = GuildSetting.get_setting(message.guild.id)
            channel_id = conf['watch_channel_id']['text']
            self.target_channel = await self.bot.fetch_channel(channel_id)

        # 読み上げ対象のチャンネル以外は読み上げない
        if message.channel != self.target_channel:
            return

        vc = self.voice_client
        if vc is None:
            return
        if vc.is_connected() is False:
            conf = GuildSetting.get_setting(message.guild.id)
            channel_id = conf['watch_channel_id']['voice']
            voice_channel = self.bot.get_channel(channel_id)
            await self.__join(self.target_channel, voice_channel)

        msg = message.clean_content
        if message.content.startswith('=sc '):
            msg = f"{message.author.display_name}さんがスパチャしました。{msg[4:]}"
        msg = self._convert_message(msg, self.read_char_cnt)
        vf = await VoiceFactory.create_voice(msg, message.author.id)
        if vf is None:
            return
        # 一定時間だけ再生を試みる
        for _ in range(600):
            try:
                vc.play(
                    discord.FFmpegPCMAudio(str(vf)),
                    after=lambda e: vf.unlink())
                break
            except discord.ClientException:
                await asyncio.sleep(0.2)
        else:
            print(f"Play canceled : {message.clean_content}")
            vf.unlink()
            # await self.target_channel.send("長い文章を読み上げているから読み上げをやめるわ")

    def get_serif(self, name: str, *args) -> str:
        '''セリフを取得'''
        if name not in self.serifs:
            return ''

        serif = self.serifs[name]
        if len(args) < 1:
            return serif
        else:
            replacements = {}
            for i in range(len(args)):
                replacements[f'${i}'] = str(args[i])

            # NOTE: 参考URL
            # https://arakan-pgm-ai.hatenablog.com/entry/2019/04/04/090000
            return re.sub('({})'.format('|'.join(map(re.escape, replacements.keys()))), lambda m: replacements[m.group()], serif)


def setup(bot):
    bot.add_cog(VoiceReading(bot))
