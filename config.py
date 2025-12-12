import os

class Config:
    SECRET_KEY = "your-secret-key"
    JWT_SECRET_KEY = "your-jwt-secret"
    
    # MySQL Connector (SQLAlchemy)
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://root:YOUR_PASSWORD@localhost/YOUR_DATABASE"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
