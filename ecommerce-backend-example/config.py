import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    CUSTOMER_DATABASE = os.getenv(
        "CUSTOMER_DATABASE",
        str((Path(__file__).parent / "db" / "ecommerce.db").resolve())
    )

config = Config()