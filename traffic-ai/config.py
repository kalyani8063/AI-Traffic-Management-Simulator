import os


class Config:
    """Global Flask configuration values."""

    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    MAPBOX_TOKEN = os.getenv('MAPBOX_TOKEN', 'pk.eyJ1Ijoia2FseWFuaTg4OTAiLCJhIjoiY21tN2JvNm5yMGxqYjJzc2dxM3M4eWd1MSJ9.zsej-9YlU9EOLouDOVGCUg')
