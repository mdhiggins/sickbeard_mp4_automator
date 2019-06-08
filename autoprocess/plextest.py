from plex import refreshPlex

class Settings:
    Plex = {}

settings = Settings
settings.Plex['host'] = "10.0.1.17"
settings.Plex['port'] = "32400"
settings.Plex['token'] = ""
settings.Plex['refresh'] = True

refreshPlex(settings, 'movie')