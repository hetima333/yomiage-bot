import re
import json
from pathlib import Path

import alkana
import romkan


class MessageConverter():
    # キャメルで単語ごとに区切られた英語を検索する
    re_eng = re.compile(r'[A-Z]?[a-z]{2,}')
    # キャメルで単語ごとに区切られたローマ字を検索する
    re_roma = re.compile(r'[A-Z]?[a-z]{2,}')

    words_file = Path('data/json/global_words.json')

    @classmethod
    def replace_eng_to_kana(cls, msg: str) -> str:
        '''
        英語をかな読み文字に置換する
        例）wood→うっど
        '''

        _msg = msg
        # 英語かな読み対応辞書の作成
        for word in cls.re_eng.findall(_msg):
            # alkanaは小文字検索
            read = alkana.get_kana(word.lower())
            if read is not None:
                _msg = _msg.replace(word, read, 1)

        return _msg

    @classmethod
    def replace_roman_to_kana(cls, msg: str) -> str:
        '''
        ローマ字をかな読み文字に置換する
        例）ninja→にんじゃ
        \n※英単語もローマ字に変換されます
        '''

        _msg = msg
        # ローマ字かなの置換
        for word in cls.re_roma.findall(_msg):
            read = romkan.to_hiragana(word)
            _msg = _msg.replace(word, read, 1)

        return _msg

    @classmethod
    def replace_by_re(cls, msg: str) -> str:
        '''
        正規表現による置換を行なう
        '''
        _msg = msg
        with cls.words_file.open() as f:
            words = json.loads(f.read())
        for k, v in words.items():
            _msg = re.sub(k, v, _msg)

        return _msg
