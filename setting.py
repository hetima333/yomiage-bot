import json
from pathlib import Path

SETTING_PATH = Path('settings')


class GuildSetting():
    GUILD_PATH = SETTING_PATH / "guild_setting.json"

    @classmethod
    def get_all_settings(cls) -> dict:
        '''全サーバーの設定を取得する'''
        with cls.GUILD_PATH.open() as f:
            return json.loads(f.read())

    @classmethod
    def get_setting(cls, guild_id: int) -> dict:
        '''サーバー設定を取得する'''
        data = cls.get_all_settings()
        return data.get(str(guild_id), data['default'])

    @classmethod
    def update_setting(cls, guild_id: int, setting: dict) -> None:
        '''サーバー設定を保存する'''
        data = cls.get_all_settings()
        data[str(guild_id)] = setting
        with cls.GUILD_PATH.open('w') as f:
            f.write(json.dumps(data, ensure_ascii=True, indent=4))


class UserSetting():
    USER_PATH = SETTING_PATH / "user_setting.json"

    @classmethod
    def get_all_settings(cls) -> dict:
        '''全ユーザーの設定を取得する'''
        with cls.USER_PATH.open() as f:
            return json.loads(f.read())

    @classmethod
    def get_setting(cls, user_id: int) -> dict:
        '''ユーザー設定を取得する'''
        data = cls.get_all_settings()
        # NOTE: 初期設定をランダム化する場合は、ここでいい感じにする
        return data.get(str(user_id), data['default'])

    @classmethod
    def update(cls, user_id: int, setting: dict) -> None:
        '''ユーザー設定を保存する'''
        data = cls.get_all_settings()
        data[str(user_id)] = setting
        with cls.USER_PATH.open('w') as f:
            f.write(json.dumps(data, ensure_ascii=True, indent=4))
