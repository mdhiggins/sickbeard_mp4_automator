try:
    from config.custom import validation
except ImportError:
    validation = None
try:
    from config.custom import blockVideoCopy
except ImportError:
    blockVideoCopy = None
try:
    from config.custom import blockAudioCopy
except ImportError:
    blockAudioCopy = None
try:
    from config.custom import skipStream
except ImportError:
    skipStream = None
try:
    from config.custom import skipUA
except ImportError:
    skipUA = None
try:
    from config.custom import streamTitle
except ImportError:
    streamTitle = None
