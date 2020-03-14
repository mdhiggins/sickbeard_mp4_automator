import sys
from babelfish import Language


def getAlpha3TCode(code, default=None):  # We need to make sure that language codes are alpha3T
    code = code.strip().lower().replace('.', '')
    lang = default or 'und'

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
