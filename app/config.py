import os

from dotenv import load_dotenv

load_dotenv()


basedir = os.path.abspath(os.path.dirname(__file__))

class Config:

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key-change-this-in-prod"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(basedir, "../instance/mecws.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SHELTER_NAME = os.environ.get("SHELTER_NAME") or "MECWS Shelter"
    WEATHER_LAT = float(os.environ.get("WEATHER_LAT") or 44.2601)
    WEATHER_LON = float(os.environ.get("WEATHER_LON") or -72.5754)

    # Mail Config
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")
