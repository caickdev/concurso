"""Filtro de profanidade em português para moderação automática de comentários.

Estratégia: normalização (remoção de acentos, leetspeak básico, espaçamento
artificial "p a l a v r ã o") + correspondência por palavras completas (regex
com fronteiras \\b em ambos os lados) contra uma lista curada de palavras e
suas flexões mais comuns, para evitar falsos positivos em palavras legítimas
que apenas contêm um radical ofensivo como substring (ex.: "computador",
"deputado", "cuidado") sem recorrer a um serviço externo síncrono no caminho
crítico de escrita.
"""
import re
import unicodedata

# Lista de palavras ofensivas em PT-BR e flexões comuns — correspondência é
# sempre por palavra inteira (não por substring), para não pegar palavras
# legítimas que contenham um destes radicais no meio (ex.: "cuidado", "disputa").
_PROFANITY_ROOTS = [
    "arrombado", "arrombada", "arrombados", "arrombadas",
    "bosta", "bostas", "buceta", "bucetas", "burra", "burro", "burros", "burras",
    "caralho", "caralhos", "cacete", "cacetes",
    "corno", "cornos", "corna", "cornas", "cuzao", "cuzão", "cuzoes", "cuzões",
    "desgracado", "desgracada", "desgraçado", "desgraçada",
    "filho da puta", "filha da puta", "fdp",
    "foda", "fodas", "fudido", "fudida", "fudidos", "fudidas",
    "gonorreia", "idiota", "idiotas", "imbecil", "imbecis",
    "merda", "merdas", "otario", "otaria", "otário", "otária", "otarios", "otarias",
    "pariu", "penis", "pênis", "piroca", "pirocas",
    "porra", "porras", "porcaria", "porcarias",
    "punheta", "punhetas", "puta", "putas", "putaria", "putarias", "putinha", "putinhas",
    "retardado", "retardada", "retardados", "retardadas",
    "safado", "safada", "safados", "safadas",
    "vadia", "vadias", "vagabundo", "vagabunda", "vagabundos", "vagabundas",
    "viado", "viados", "xoxota", "xoxotas",
]

_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s",
})

_PROFANITY_REGEX = re.compile(
    r"\b(?:" + "|".join(re.escape(root) for root in _PROFANITY_ROOTS) + r")\b",
    flags=re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    text = text.lower()
    text = _strip_accents(text)
    text = text.translate(_LEET_MAP)
    # Remove espaçamento artificial entre letras isoladas (ex.: "p o r r a")
    text = re.sub(r"\b([a-z])\s+(?=[a-z]\b)", r"\1", text)
    # Colapsa repetições excessivas de caracteres (ex.: "poooorra" -> "porra")
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def contains_profanity(text: str) -> bool:
    if not text:
        return False
    normalized = normalize_text(text)
    return bool(_PROFANITY_REGEX.search(normalized))


def find_matches(text: str) -> list[str]:
    normalized = normalize_text(text)
    return _PROFANITY_REGEX.findall(normalized)
