class ConfigError(Exception):
    """Bad configuration is a defect: raised while building the app so a bad deploy dies at boot."""
