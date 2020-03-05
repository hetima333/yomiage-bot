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
    VOICES = {
        'normal': SYS_VOICE_DIR / 'mei/mei_normal.htsvoice',
        'happy': SYS_VOICE_DIR / 'mei/mei_happy.htsvoice',
        'bashful': SYS_VOICE_DIR / 'mei/mei_bashful.htsvoice',
        'angry': SYS_VOICE_DIR / 'mei/mei_angry.htsvoice',
        'sad': SYS_VOICE_DIR / 'mei/mei_sad.htsvoice',
        'male': SYS_VOICE_DIR / 'm100/nitech_jp_atr503_m001.htsvoice',
        'miku': SYS_VOICE_DIR / 'miku/miku.htsvoice',
    }

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
    async def create_voice(cls, msg: str, user_id: int) -> Path:
        with cls.SOUND_LINK_FILE.open() as f:
            sounds = json.loads(f.read())

        for k, v in sounds.items():
            r = re.fullmatch(f"^{k}$", msg)
            if r is not None:
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

        voice_file = cls.VOICES[setting['voice']]
        cmd = [
            'open_jtalk',
            '-x', str(cls.DICT_DIR),
            '-m', str(voice_file),
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
