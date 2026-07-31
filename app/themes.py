"""Menyu uslublari.

Har uslub — alohida dizayn, faqat boshqa rang emas. O'zgaradigan narsalar:
palitra (fon, qog'oz, matn), tipografika, burchak yumaloqligi. Bundan tashqari
`style.css` da `[data-theme="..."]` bloklari bor — ular soya, chegara va
sarlavha bezagi kabi tuzilmaviy farqlarni beradi.

Shuning uchun bu yerda rang emas, **butun palitra** saqlanadi: fon iliq qog'oz
bo'lsa, matn ham iliq bo'lishi kerak, aks holda uslub pachoq ko'rinadi.
"""

import re
from dataclasses import dataclass, field

from markupsafe import Markup

SYSTEM_SANS = (
    'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif'
)
SERIF = '"Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif'
ROUNDED = '"SF Pro Rounded", ui-rounded, "Nunito", ' + SYSTEM_SANS


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    hint: str
    accent: str
    variables: dict[str, str] = field(default_factory=dict)

    def css(self, accent: str) -> str:
        pairs = {"--accent": accent, **self.variables}
        return "".join(f"{name}:{value};" for name, value in pairs.items())


THEMES: dict[str, Theme] = {
    # Sovuq oq, yumshoq soyalar — bugungi ilovalar tili
    "zamonaviy": Theme(
        key="zamonaviy",
        name="Zamonaviy",
        hint="Toza oq, yumshoq soyalar — kafe va qahvaxonalar uchun",
        accent="#b45309",
        variables={
            "--page": "#f7f8fa",
            "--surface": "#ffffff",
            "--surface-2": "#f2f3f5",
            "--surface-3": "#e9ebef",
            "--ink": "#0f1115",
            "--ink-2": "#6b7280",
            "--ink-3": "#9ca3af",
            "--line": "#eceef1",
            "--line-2": "#dfe2e7",
            "--font-sans": SYSTEM_SANS,
            "--font-head": SYSTEM_SANS,
            "--head-spacing": "-.025em",
            "--r-sm": "10px",
            "--r-md": "12px",
            "--r-lg": "16px",
            "--r-xl": "24px",
            "--r-full": "999px",
        },
    ),
    # Iliq qog'oz, serif, soyasiz — chop etilgan restoran menyusi hissi
    "klassik": Theme(
        key="klassik",
        name="Klassik",
        hint="Iliq qog'oz va serif sarlavhalar — milliy oshxona va restoranlar",
        accent="#7c2d12",
        variables={
            "--page": "#f7f2ea",
            "--surface": "#fffdf9",
            "--surface-2": "#f2ebe0",
            "--surface-3": "#e8dfd1",
            "--ink": "#211a14",
            "--ink-2": "#6b5b4a",
            "--ink-3": "#9c8a76",
            "--line": "#e5dbcd",
            "--line-2": "#d6c8b4",
            "--font-sans": SYSTEM_SANS,
            "--font-head": SERIF,
            "--head-spacing": "0",
            "--r-sm": "3px",
            "--r-md": "3px",
            "--r-lg": "4px",
            "--r-xl": "4px",
            "--r-full": "3px",
        },
    ),
    # Shaftoli fon, juda yumaloq, chegarasiz — shirinlik do'koni
    "issiq": Theme(
        key="issiq",
        name="Issiq",
        hint="Shaftoli tuslar, juda yumaloq shakllar — shirinlik va non mahsulotlari",
        accent="#c2410c",
        variables={
            "--page": "#fff6ef",
            "--surface": "#ffffff",
            "--surface-2": "#fdece1",
            "--surface-3": "#f9dcc9",
            "--ink": "#2b1a12",
            "--ink-2": "#7c6255",
            "--ink-3": "#a89184",
            "--line": "#f8e3d4",
            "--line-2": "#f0d0b8",
            "--font-sans": ROUNDED,
            "--font-head": ROUNDED,
            "--head-spacing": "-.015em",
            "--r-sm": "14px",
            "--r-md": "20px",
            "--r-lg": "26px",
            "--r-xl": "32px",
            "--r-full": "999px",
        },
    ),
    # Sof oq, qora urg'u, faqat ingichka chiziqlar — rang faqat fotolardan
    "minimal": Theme(
        key="minimal",
        name="Minimal",
        hint="Sof oq va qora, bezaksiz — taom fotosuratlari o'zi gapiradi",
        accent="#18181b",
        variables={
            "--page": "#ffffff",
            "--surface": "#ffffff",
            "--surface-2": "#f4f4f5",
            "--surface-3": "#e4e4e7",
            "--ink": "#09090b",
            "--ink-2": "#71717a",
            "--ink-3": "#a1a1aa",
            "--line": "#e4e4e7",
            "--line-2": "#d4d4d8",
            "--font-sans": SYSTEM_SANS,
            "--font-head": SYSTEM_SANS,
            "--head-spacing": "-.04em",
            "--r-sm": "2px",
            "--r-md": "2px",
            "--r-lg": "2px",
            "--r-xl": "2px",
            "--r-full": "2px",
        },
    ),
}

DEFAULT_THEME = "zamonaviy"

HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def get(key: str | None) -> Theme:
    return THEMES.get(key or "", THEMES[DEFAULT_THEME])


def safe_accent(theme: Theme, accent: str | None) -> str:
    """Faqat haqiqiy hex rangni o'tkazadi.

    Rang <style> ichiga tushadi, ya'ni u yerdan `</style>` yozib chiqib ketish
    mumkin edi. Shakl mos kelmasa uslubning o'z rangiga qaytamiz.
    """
    if accent and HEX_COLOR.match(accent.strip()):
        return accent.strip()
    return theme.accent


def css_variables(theme: Theme, accent: str | None = None) -> Markup:
    """Menyu sahifasining <head> ichiga qo'yiladigan o'zgaruvchilar.

    Markup qaytariladi: shrift nomlaridagi qo'shtirnoqlar Jinja tomonidan
    `&#34;` ga aylansa CSS buziladi. Ichkariga tushadigan yagona tashqi qiymat —
    rang, u yuqorida tekshiriladi.
    """
    return Markup(theme.css(safe_accent(theme, accent)))
