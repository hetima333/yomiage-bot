import json
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


class Config():
    CONFIG_PATH = Path('config')

    @classmethod
    def get_global(cls) -> dict:
        '''全体の設定を取得する'''
        path = cls.CONFIG_PATH / "global.json"
        with path.open() as f:
            return json.loads(f.read())

    @classmethod
    def get_prefix(cls) -> str:
        return cls.get_global()['prefix']

    @classmethod
    def get_token(cls) -> str:
        return os.environ['DISCORD_BOT_TOKEN']
