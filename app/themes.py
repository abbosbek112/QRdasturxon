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
    # Qorong'i fon — yagona uslub bo'lib, kechqurun ishlaydigan joylar uchun.
    # Matn ataylab sof oq emas: qora fonda sof oq ko'zni charchatadi.
    "tungi": Theme(
        key="tungi",
        name="Tungi",
        hint="Qorong'i fon, yorqin urg'u — bar, lounge va kechki restoranlar",
        accent="#f59e0b",
        variables={
            "--page": "#0b0d10",
            "--surface": "#14171c",
            "--surface-2": "#1c2027",
            "--surface-3": "#262b33",
            "--ink": "#e8eaed",
            "--ink-2": "#9aa1ab",
            "--ink-3": "#6c737d",
            "--line": "#242931",
            "--line-2": "#333a44",
            "--font-sans": SYSTEM_SANS,
            "--font-head": SYSTEM_SANS,
            "--head-spacing": "-.03em",
            "--r-sm": "8px",
            "--r-md": "12px",
            "--r-lg": "16px",
            "--r-xl": "22px",
            "--r-full": "999px",
        },
    ),
    # Sovuq yashil, tabiiy tuslar — sabzavot va sog'lom taomlar
    "bogh": Theme(
        key="bogh",
        name="Bog'",
        hint="Yashil va tabiiy tuslar — sog'lom taomlar va sabzavotli menyu",
        accent="#15803d",
        variables={
            "--page": "#f4f8f3",
            "--surface": "#ffffff",
            "--surface-2": "#e9f1e7",
            "--surface-3": "#d9e7d6",
            "--ink": "#12210f",
            "--ink-2": "#5b6b57",
            "--ink-3": "#8b9a87",
            "--line": "#e0eade",
            "--line-2": "#cadcc5",
            "--font-sans": SYSTEM_SANS,
            "--font-head": SERIF,
            "--head-spacing": "-.01em",
            "--r-sm": "8px",
            "--r-md": "14px",
            "--r-lg": "18px",
            "--r-xl": "26px",
            "--r-full": "999px",
        },
    ),
    # Sovuq ko'k — baliq, dengiz mahsulotlari va yozgi terassalar
    "dengiz": Theme(
        key="dengiz",
        name="Dengiz",
        hint="Sovuq ko'k tuslar — baliq, dengiz mahsulotlari va yozgi terassa",
        accent="#0369a1",
        variables={
            "--page": "#f2f7fb",
            "--surface": "#ffffff",
            "--surface-2": "#e6eff7",
            "--surface-3": "#d3e3ef",
            "--ink": "#0c1a24",
            "--ink-2": "#54687a",
            "--ink-3": "#8497a6",
            "--line": "#dde9f2",
            "--line-2": "#c4d8e7",
            "--font-sans": SYSTEM_SANS,
            "--font-head": SYSTEM_SANS,
            "--head-spacing": "-.02em",
            "--r-sm": "10px",
            "--r-md": "14px",
            "--r-lg": "18px",
            "--r-xl": "26px",
            "--r-full": "999px",
        },
    ),
    # To'q zarhal va serif — qimmat restoran hissi
    "qirol": Theme(
        key="qirol",
        name="Qirol",
        hint="To'q ranglar va serif — qimmat restoran va bayram ziyofatlari",
        accent="#a16207",
        variables={
            "--page": "#faf7f2",
            "--surface": "#ffffff",
            "--surface-2": "#f3ede3",
            "--surface-3": "#e7ddcd",
            "--ink": "#1c1917",
            "--ink-2": "#5f574e",
            "--ink-3": "#928878",
            "--line": "#ebe3d7",
            "--line-2": "#dbcfbd",
            "--font-sans": SERIF,
            "--font-head": SERIF,
            "--head-spacing": ".01em",
            "--r-sm": "2px",
            "--r-md": "6px",
            "--r-lg": "8px",
            "--r-xl": "10px",
            "--r-full": "999px",
        },
    ),
}

DEFAULT_THEME = "zamonaviy"

# Urg'u rangi uchun tayyor tanlov. Egasi rang tanlagichni ochib o'ylab
# o'tirmasin: bu ranglar oq fonda ham, qorong'i fonda ham o'qiladigan
# darajada to'q — och rang tanlangan tugmadagi oq yozuvni yo'q qilardi.
ACCENTS: tuple[str, ...] = (
    "#b45309",  # g'ishtrang
    "#c2410c",  # to'q sariq
    "#b91c1c",  # qizil
    "#a16207",  # zarhal
    "#15803d",  # yashil
    "#0f766e",  # ko'kimtir yashil
    "#0369a1",  # ko'k
    "#4338ca",  # siyoh
    "#7e22ce",  # binafsha
    "#be185d",  # pushti
    "#7c2d12",  # jigarrang
    "#18181b",  # qora
)

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
