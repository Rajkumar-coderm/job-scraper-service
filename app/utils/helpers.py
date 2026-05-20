from urllib.parse import quote


def clean_text(value):
    if not value:
        return "N/A"

    return value.strip()


def make_search_keyword(keyword: str):
    return quote(keyword)