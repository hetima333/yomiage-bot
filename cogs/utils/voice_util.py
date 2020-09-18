import io
import aiohttp
import time
import os
import json
import re
import subprocess
from copy import copy
from pathlib import Path
from .math_util import MathUtility
from setting import UserSetting


class VoiceFactory():
    TEMP_DIR = Path('/tmp')
    DICT_DIR = Path(os.environ['DIC_DIR'])
    SYS_VOICE_DIR = Path(os.environ['SYS_VOICE_DIR'])
    SOUND_LINK_FILE = Path('../lunalu-bot/data/json/sound_links.json')
    VOICE_LINK_FILE = Path('../lunalu-bot/data/json/voice_links.json')
    SOUND_LOG_FILE = Path('../lunalu-bot/data/json/sound_log.json')

    @classmethod
    def get_user_setting(cls, user_id: int) -> dict:
        setting = UserSetting.get_setting(user_id)
        # NOTE: ユーザー設定内のパラメータは0~100の数値なので/100.0している
        _setting = copy(setting)
        _setting['speed'] = MathUtility.lerp(
            0.5, 2.0, setting['speed'] / 100.0)
        _setting['tone'] = MathUtility.lerp(
            -20.0, 20.0, setting['tone'] / 100.0)
        _setting['intone'] = MathUtility.lerp(
            0.0, 4.0, setting['intone'] / 100.0)
        _setting['threshold'] = MathUtility.lerp(
            0.0, 1.0, setting['threshold'] / 100.0)
        _setting['volume'] = MathUtility.lerp(
            -20.0, 0.0, setting['volume'] / 100.0)
        # TODO: 他のパラメータを追加する(all-pass？)

        return _setting

    @classmethod
    def get_sound_list(cls) -> dict:
        with cls.SOUND_LINK_FILE.open() as f:
            sounds = json.loads(f.read())

        return sounds

    @classmethod
    def get_voice_list(cls) -> dict:
        with cls.VOICE_LINK_FILE.open() as f:
            voices = json.loads(f.read())

        return voices

    @classmethod
    async def create_voice(cls, msg: str, user_id: int) -> Path:
        with cls.SOUND_LINK_FILE.open() as f:
            sounds = json.loads(f.read())

        # 全角チルダを波ダッシュに置換
        msg = msg.replace('\uff5e', '\u301c')

        for v in sounds:
            r = re.fullmatch(f"{v['reg']}", msg, re.I)
            if r is not None:
                # 語録使用回数を追加
                # ファイルを開く
                with cls.SOUND_LOG_FILE.open() as f:
                    logs = json.loads(f.read())
                counts = logs['user_data'].get(str(user_id), [0] * logs['sound_count'])
                # IDは1から開始しているため-1する
                sound_id = int(v['id']) - 1
                counts[sound_id] = counts[sound_id] + 1
                logs['user_data'][str(user_id)] = counts
                # 回数を更新して上書き
                with cls.SOUND_LOG_FILE.open('w') as f:
                    f.write(json.dumps(logs))
                return await cls.create_voice_from_url(v['link'])

        return await cls.create_voice_from_openjtalk(msg, user_id)

    @classmethod
    async def create_voice_from_url(cls, url: str) -> Path:
        # 拡張子の取得
        _, ext = os.path.splitext(url)
        ftime = time.perf_counter()
        file_name = f'voice_{ftime}'
        file_path = cls.TEMP_DIR / f'{file_name}{ext}'

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status != 200:
                    # NOTE: いい感じのエラーにする？
                    return None
                with file_path.open('wb') as f:
                    data = await r.read()
                    f.write(data)
                return file_path

    @classmethod
    async def create_voice_from_openjtalk(cls, t, user_id: int) -> Path:
        ftime = time.perf_counter()
        text_file = cls.TEMP_DIR / f'voice_{ftime}.txt'
        setting = cls.get_user_setting(user_id)

        with text_file.open('w') as f:
            f.write(t)

        file_name = f'voice_{ftime}'
        file_path = cls.TEMP_DIR / f'{file_name}.wav'

        with cls.VOICE_LINK_FILE.open() as f:
            voice_file = json.loads(f.read())

        cmd = [
            'open_jtalk',
            '-x', str(cls.DICT_DIR),
            '-m', str(cls.SYS_VOICE_DIR / f"{voice_file[setting['voice']]}.htsvoice"),
            '-ow', str(file_path),
            '-r', str(setting['speed']),
            '-fm', str(setting['tone']),
            '-jf', str(setting['intone']),
            '-u', str(setting['threshold']),
            # NOTE: Linuxだと音量が無効なオプションと言われるので一旦避難
            # '-g', str(setting['volume']),
        ]
        cmd.append(str(text_file))

        subprocess.run(cmd)
        text_file.unlink()

        # wav → mp3変換
        # NOTE: 変換しなくても再生はされるけど警告がめっちゃでる
        # audio_segment = AudioSegment.from_file(str(wav_file), format='wav')
        # wav_file.unlink()
        # audio_segment.export(str(mp3_file), format='mp3')

        return file_path
