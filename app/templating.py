from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.i18n import LANGUAGES, t, tr
from app.security import csrf_token

templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")
templates.env.globals.update(t=t, tr=tr, csrf_token=csrf_token, LANGUAGES=LANGUAGES)


def format_price(value) -> str:
    return f"{int(value):,}".replace(",", " ")


templates.env.filters["price"] = format_price
