"""Menyu uslublari.

Har uslub — alohida DIZAYN TILI, boshqa rang emas. Farq uch qatlamda:

1. Palitra — bu yerda, `variables` ichida.
2. Tipografika va burchak yumaloqligi — ham shu yerda.
3. TUZILMA — `style.css` dagi `[data-theme="..."]` bloklarida: soya
   turi, chegara qalinligi, kartochka shakli, sarlavha bezagi.

Uchinchisi eng muhimi. Bir paytlar uchta uslub faqat rang bilan farq
qilardi va ular yonma-yon qo'yilganda bir xil ko'rinardi — egasi
"nima farqi bor?" deb haqli savol berdi.

Har uslub tanilgan dizayn maktabidan olingan, shuning uchun ular
bir-biriga o'xshamaydi: yumshoq soya (neomorfizm) bilan qalin qora
chegara (brutalizm) bitta menyuda turolmaydi.
"""

import re
from dataclasses import dataclass, field

from markupsafe import Markup

SYSTEM_SANS = (
    'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif'
)
SERIF = '"Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif'
ROUNDED = '"SF Pro Rounded", ui-rounded, "Nunito", ' + SYSTEM_SANS
MONO = '"SF Mono", ui-monospace, "Cascadia Mono", Consolas, monospace'
GROTESK = '"Arial Black", "Helvetica Neue", Impact, sans-serif'


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
    # 1. MINIMALIZM — bezak yo'q, bo'sh joy ko'p. Rang faqat fotodan keladi.
    "minimal": Theme(
        key="minimal",
        name="Minimal",
        hint="Bezaksiz, ko'p bo'sh joy — taom fotosurati o'zi gapiradi",
        accent="#18181b",
        variables={
            "--page": "#ffffff", "--surface": "#ffffff",
            "--surface-2": "#f4f4f5", "--surface-3": "#e4e4e7",
            "--ink": "#09090b", "--ink-2": "#71717a", "--ink-3": "#a1a1aa",
            "--line": "#e4e4e7", "--line-2": "#d4d4d8",
            "--font-sans": SYSTEM_SANS, "--font-head": SYSTEM_SANS,
            "--head-spacing": "-.04em",
            "--r-sm": "2px", "--r-md": "2px", "--r-lg": "2px",
            "--r-xl": "2px", "--r-full": "2px",
        },
    ),
    # 2. NEOMORFIZM — element fondan bo'rtib chiqqandek. Buning ishlashi
    # uchun fon va kartochka RANGI BIR XIL bo'lishi shart: butun ta'sir
    # ikki tomonlama soyadan keladi, chegaradan emas.
    "neomorf": Theme(
        key="neomorf",
        name="Neomorfizm",
        hint="Yumshoq soyalar, bo'rtib chiqqan shakllar — zamonaviy qahvaxona",
        accent="#6366f1",
        variables={
            "--page": "#e8ecf3", "--surface": "#e8ecf3",
            "--surface-2": "#e2e7ef", "--surface-3": "#d8dfe9",
            "--ink": "#28303f", "--ink-2": "#697386", "--ink-3": "#94a0b4",
            "--line": "#e8ecf3", "--line-2": "#d8dfe9",
            "--font-sans": ROUNDED, "--font-head": ROUNDED,
            "--head-spacing": "-.02em",
            "--r-sm": "14px", "--r-md": "20px", "--r-lg": "26px",
            "--r-xl": "34px", "--r-full": "999px",
        },
    ),
    # 3. GLASSMORFIZM — xira shisha. Fon rangli bo'lishi shart, aks holda
    # shaffoflikning ortida ko'rinadigan narsa qolmaydi va effekt yo'qoladi.
    "glass": Theme(
        key="glass",
        name="Glassmorfizm",
        hint="Xira shisha kartochkalar, rangli fon — bar va lounge",
        accent="#a855f7",
        variables={
            "--page": "#1a1033", "--surface": "#ffffff14",
            "--surface-2": "#ffffff1f", "--surface-3": "#ffffff2b",
            "--ink": "#f4f1fb", "--ink-2": "#c3bad9", "--ink-3": "#9288b0",
            "--line": "#ffffff2b", "--line-2": "#ffffff42",
            "--font-sans": SYSTEM_SANS, "--font-head": SYSTEM_SANS,
            "--head-spacing": "-.03em",
            "--r-sm": "12px", "--r-md": "16px", "--r-lg": "22px",
            "--r-xl": "28px", "--r-full": "999px",
        },
    ),
    # 4. YASSI — gradient ham, soya ham, 3D ham yo'q. Faqat tekis rang
    # va aniq chegara. Rang to'yingan bo'lishi kerak: yassi dizaynda
    # ajratuvchi yagona vosita — rangning o'zi.
    "yassi": Theme(
        key="yassi",
        name="Yassi",
        hint="Soyasiz, tekis ranglar — tez ovqatlanish va yetkazib berish",
        accent="#e11d48",
        variables={
            "--page": "#f1f5f9", "--surface": "#ffffff",
            "--surface-2": "#e2e8f0", "--surface-3": "#cbd5e1",
            "--ink": "#0f172a", "--ink-2": "#475569", "--ink-3": "#94a3b8",
            "--line": "#cbd5e1", "--line-2": "#94a3b8",
            "--font-sans": SYSTEM_SANS, "--font-head": SYSTEM_SANS,
            "--head-spacing": "-.01em",
            "--r-sm": "4px", "--r-md": "6px", "--r-lg": "8px",
            "--r-xl": "10px", "--r-full": "999px",
        },
    ),
    # 5. MATERIAL — qog'oz va siyoh. Har qatlam o'z balandligiga ega va
    # soya aynan shu balandlikni ko'rsatadi, bezak uchun emas.
    "material": Theme(
        key="material",
        name="Material",
        hint="Qatlamli soyalar, aniq tuzilma — kafe va qahvaxonalar",
        accent="#00695c",
        variables={
            "--page": "#fafafa", "--surface": "#ffffff",
            "--surface-2": "#f5f5f5", "--surface-3": "#eeeeee",
            "--ink": "#212121", "--ink-2": "#616161", "--ink-3": "#9e9e9e",
            "--line": "#eeeeee", "--line-2": "#e0e0e0",
            "--font-sans": SYSTEM_SANS, "--font-head": SYSTEM_SANS,
            "--head-spacing": "0",
            "--r-sm": "4px", "--r-md": "8px", "--r-lg": "12px",
            "--r-xl": "16px", "--r-full": "999px",
        },
    ),
    # 6. BRUTALIZM — qalin qora chegara, ulkan shrift, keskin kontrast.
    # Soya bor, lekin yumshoq emas: u qattiq, siljigan qora to'rtburchak.
    "brutal": Theme(
        key="brutal",
        name="Brutalizm",
        hint="Qalin chiziq, yirik shrift, keskin rang — ko'cha ovqati va fast-food",
        accent="#facc15",
        variables={
            "--page": "#fefce8", "--surface": "#ffffff",
            "--surface-2": "#fef9c3", "--surface-3": "#fef08a",
            "--ink": "#000000", "--ink-2": "#292524", "--ink-3": "#57534e",
            "--line": "#000000", "--line-2": "#000000",
            "--font-sans": SYSTEM_SANS, "--font-head": GROTESK,
            "--head-spacing": "-.04em",
            "--r-sm": "0px", "--r-md": "0px", "--r-lg": "0px",
            "--r-xl": "0px", "--r-full": "0px",
        },
    ),
    # 7. SKEYOMORFIZM — haqiqiy buyumga o'xshatish: qog'oz teksturasi,
    # ipli chekka, biroz sarg'aygan varaq. Chop etilgan menyu hissi.
    "skeyo": Theme(
        key="skeyo",
        name="Skeyomorfizm",
        hint="Qog'oz teksturasi va serif — milliy oshxona, chop etilgan menyu hissi",
        accent="#78350f",
        variables={
            "--page": "#e8ddc8", "--surface": "#fdf8ec",
            "--surface-2": "#f3e9d2", "--surface-3": "#e6d8ba",
            "--ink": "#2b2013", "--ink-2": "#6b5940", "--ink-3": "#9a866a",
            "--line": "#d9c9a8", "--line-2": "#c2ad86",
            "--font-sans": SERIF, "--font-head": SERIF,
            "--head-spacing": "0",
            "--r-sm": "2px", "--r-md": "3px", "--r-lg": "4px",
            "--r-xl": "5px", "--r-full": "3px",
        },
    ),
    # 8. TIPOGRAFIK — asosiy urg'u shriftda. Rasm kichrayadi, nom esa
    # o'sadi va katta harflar bilan yoziladi.
    "tipografik": Theme(
        key="tipografik",
        name="Tipografik",
        hint="Rasm emas, shrift gapiradi — vinoxona, qahva va mualliflik oshxonasi",
        accent="#0f766e",
        variables={
            "--page": "#faf9f7", "--surface": "#ffffff",
            "--surface-2": "#f2f0ec", "--surface-3": "#e6e3dd",
            "--ink": "#1c1917", "--ink-2": "#57534e", "--ink-3": "#a8a29e",
            "--line": "#e7e5e4", "--line-2": "#d6d3d1",
            "--font-sans": SYSTEM_SANS, "--font-head": SERIF,
            "--head-spacing": "-.02em",
            "--r-sm": "0px", "--r-md": "0px", "--r-lg": "0px",
            "--r-xl": "0px", "--r-full": "0px",
        },
    ),
}

# Eski kalitlar yangilariga bog'lanadi.
#
# Uslublar qayta yozilganda kalitlar ham o'zgardi. Bazadagi eski qiymat
# `themes.get()` da standartga tushib ketardi va restoran menyusi bir
# kechada boshqa ko'rinishga o'tib qolardi. Bu jadval shuni to'sadi:
# har eski uslub o'ziga eng yaqin yangisiga o'tadi.
LEGACY_KEYS = {
    "zamonaviy": "material",   # toza oq, yumshoq soya
    "klassik": "skeyo",        # iliq qog'oz va serif
    "issiq": "neomorf",        # yumshoq, juda yumaloq
    "tungi": "glass",          # qorong'i fon
    "bogh": "yassi",           # soyasiz, tekis
    "dengiz": "yassi",
    "qirol": "tipografik",     # serif, bezakli
}

DEFAULT_THEME = "material"

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
    """Kalit bo'yicha uslub. Eski nomlar ham tushuniladi.

    Eski kalit uchraganda u yangisiga o'giriladi. Busiz bazadagi
    "zamonaviy" standartga tushib ketardi va restoran menyusi bir
    kechada boshqa ko'rinishga o'tib qolardi — egasi hech narsaga
    tegmagan bo'lsa ham.
    """
    key = key or ""
    key = LEGACY_KEYS.get(key, key)
    return THEMES.get(key, THEMES[DEFAULT_THEME])


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
