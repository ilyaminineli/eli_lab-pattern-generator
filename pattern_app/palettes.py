from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    key: str
    name: str
    colors: tuple[tuple[int, int, int], ...]


def _rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i: i + 2], 16) for i in (0, 2, 4))


def _palette(key: str, name: str, values: str) -> Palette:
    return Palette(key, name, tuple(_rgb(value) for value in values.split()))


# Curated LGBTQIA+ catalogue.  The source palette set is kept data-driven so new
# flags can be added without changing the renderer.
DATA = [
    ("baker78", "Original 8-Stripe Rainbow (1978)", "ff69b4 ff0000 ff8e00 ffff00 008e00 00c0c0 400098 8e008e"),
    ("rainbow", "Rainbow Pride", "e40303 ff8c00 ffed00 008026 004dff 750787"),
    ("progress", "Progress Pride", "e40303 ff8c00 ffed00 008026 004dff 750787 ffffff ffafc8 74d7ee 613915 000000"),
    ("aceflux", "Aceflux", "c62253 c12678 c0279a a928ac 8c26ae"),
    ("achillean", "Achillean", "99c6ea f9fdea acdd4d 659533"),
    ("abrosexual", "Abrosexual", "65c286 b4e4cc ffffff e796b7 d9446e"),
    ("agender", "Agender", "010204 bcc4c6 e9edee b8f483"),
    ("aroace", "Aroace", "e28c00 eccd00 ffffff 62aedc 203856"),
    ("aromantic", "Aromantic", "3da542 a7d379 ffffff a9a9a9 000000"),
    ("asexual", "Asexual", "000000 a3a3a3 ffffff 800080"),
    ("bear", "International Bear Brotherhood", "623804 d56300 fedd63 fee6b8 ffffff 555555 000000"),
    ("bigender", "Bigender", "c479a2 eda5cd d6c7e8 ffffff 9ac7e8 6d82d1"),
    ("bisexual", "Bisexual", "d0006f 8c4799 0033a0"),
    ("demiboy", "Demiboy", "7f7f7f c4c4c4 9ad9eb ffffff"),
    ("demigirl", "Demigirl", "7f7f7f c4c4c4 ffaec9 ffffff"),
    ("demiromantic", "Demiromantic", "000000 ffffff 338a37 d2d2d2"),
    ("demisexual", "Demisexual", "000000 ffffff 6e0070 d2d2d2"),
    ("gay", "Gay Men", "078d70 26ceaa 99e8c2 ffffff 7bade3 5049cb 3e1a78"),
    ("genderfluid", "Genderfluid", "ff75a2 f5f5f5 be18d6 2c2c2c 333ebd"),
    ("genderflux", "Genderflux", "f47694 f2a3b9 cecece 7ce0f7 3ecdf9 fff48e"),
    ("genderqueer", "Genderqueer", "b57edc ffffff 4a8123"),
    ("grayromantic", "Grayromantic", "087d16 b2b2b2 ffffff"),
    ("graysexual", "Graysexual", "740195 b2b2b2 ffffff"),
    ("intersex", "Intersex", "ffd800 7902aa"),
    ("leather", "Leather / Latex / BDSM", "18186b 000000 e70039"),
    ("lesbian", "Lesbian (7-Stripe / Orange-Pink)", "d52d00 ef7627 ff9a56 ffffff d162a4 b55690 a30262"),
    ("labrys", "Labrys Lesbian", "993399 000000 ffffff"),
    ("lipstick", "Lipstick Lesbian", "a40061 b75592 d063a6 e4accf ededeb c54e54 8a1e04 f30943"),
    ("maverique", "Maverique", "fff344 ffffff f49622"),
    ("nonbinary", "Nonbinary", "fff433 fff8e7 9b59d0 2d2d2d"),
    ("omnisexual", "Omnisexual", "fc9ccc fc54bc 240444 645cfc 8ca4fc"),
    ("pangender", "Pangender", "fff798 feddcc ffebfc ffffff"),
    ("pansexual", "Pansexual", "ff218c ffd800 21b1ff"),
    ("polyamory", "Polyamory (Pi)", "0000ff ff0000 000000 ffff00"),
    ("polyamory-heart", "Polyamory (Heart)", "ffffff fcbf00 009fe3 e50051 340c46"),
    ("polysexual", "Polysexual", "f61cb9 07d569 1c92f6"),
    ("queer", "Queer", "000000 99d9ea 00a2e8 b5e61d ffffff ffc90e fd6666 ffaec9"),
    ("sapphic", "Sapphic", "fd8ba8 ffffff c76bc5 fff71e f996c9"),
    ("transfeminine", "Transfeminine", "73deff ffe0ed ffb5d5 ff8cbe"),
    ("transgender", "Transgender", "5bcefa f5a9b8 ffffff"),
    ("transmasculine", "Transmasculine", "ff8abd cdf5fe 9aebff 74dfff"),
    ("xenogender", "Xenogender", "ff6691 ff9997 ffb782 fbffa6 84bbff 9c84ff a317ff ffffff"),
    ("disability", "Disability Pride", "585858 3aaf7d 7ac1e0 e9e9e9 feed77 cf7280"),
]

PRIDE_PALETTES = {key: _palette(key, name, values) for key, name, values in DATA}
PRIDE_PALETTES.update(
    {
        "ace": PRIDE_PALETTES["asexual"],
        "aro": PRIDE_PALETTES["aromantic"],
        "bi": PRIDE_PALETTES["bisexual"],
        "pan": PRIDE_PALETTES["pansexual"],
        "trans": PRIDE_PALETTES["transgender"],
        "gwen": PRIDE_PALETTES["lesbian"],
        "howell": PRIDE_PALETTES["polyamory-heart"],
        "evans": PRIDE_PALETTES["polyamory"],
    }
)

BUILTIN_PALETTES = {
    "neon": _palette("neon", "Neon", "ff3278 3cffb4 5a78ff ffdb3c e150ff"),
    "earth": _palette("earth", "Earth", "523828 9b6e46 d6bb8c 485d3e 1e1e1e"),
    "mono": _palette("mono", "Monochrome", "1e1e1e 5a5a5a 969696 dcdcdc"),
    "ice": _palette("ice", "Ice", "d2f0ff 82cdf0 4696c8 ebfaff 2d5578"),
    "ritual": _palette("ritual", "Ritual", "181212 641e1e a0372d d78c46 ebd296"),
}

ALL_PALETTES = {**BUILTIN_PALETTES, **PRIDE_PALETTES}
ALL_LGBTQ_COLORS = tuple(dict.fromkeys(color for key, _, _ in DATA for color in PRIDE_PALETTES[key].colors))


def canonical_keys() -> list[str]:
    return list(BUILTIN_PALETTES) + [key for key, _, _ in DATA]
