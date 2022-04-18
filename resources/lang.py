from babelfish import Language
from converter.avcodecs import BaseCodec


def getAlpha3TCode(code, default=None):
    lang = default or BaseCodec.UNDEFINED
    if not code or code == BaseCodec.UNDEFINED:
        return lang

    code = code.strip().lower().replace('.', '')

    if len(code) == 3:
        try:
            lang = Language(code).alpha3t
        except:
            try:
                lang = Language.fromalpha3b(code).alpha3t
            except:
                try:
                    lang = Language.fromalpha3t(code).alpha3t
                except:
                    pass
    elif len(code) == 2:
        try:
            lang = Language.fromalpha2(code).alpha3t
        except:
            pass
    return lang


def getAlpha2BCode(code, default=None):
    lang = default or BaseCodec.UNDEFINED
    if not code or code == BaseCodec.UNDEFINED:
        return lang

    code = code.strip().lower().replace('.', '')

    if len(code) == 3:
        try:
            lang = Language(code).alpha2
        except:
            try:
                lang = Language.fromalpha3b(code).alpha2
            except:
                try:
                    lang = Language.fromalpha3t(code).alpha2
                except:
                    pass
    elif len(code) == 2:
        try:
            lang = Language.fromalpha2(code).alpha2
        except:
            pass
    return lang
