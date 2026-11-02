"""Calcula estadísticas de los repos del usuario y las escribe en el README.

Solo usa la librería estándar. Lee el token de GH_TOKEN y reemplaza el bloque
entre <!-- REPO-COUNT:START --> y <!-- REPO-COUNT:END --> del README.
No publica nombres de repos: solo cantidades.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

README = sys.argv[1] if len(sys.argv) > 1 else "README.md"
TOKEN = os.environ["GH_TOKEN"]

LANG_COLORS = {
    "Python": ("3776AB", "python", "white"),
    "TypeScript": ("3178C6", "typescript", "white"),
    "JavaScript": ("F7DF1E", "javascript", "black"),
    "HTML": ("E34F26", "html5", "white"),
    "CSS": ("663399", "css", "white"),
    "C#": ("512BD4", "dotnet", "white"),
    "Java": ("ED8B00", "openjdk", "white"),
    "Kotlin": ("7F52FF", "kotlin", "white"),
    "Dart": ("0175C2", "dart", "white"),
    "PHP": ("777BB4", "php", "white"),
    "Shell": ("4EAA25", "gnubash", "white"),
    "PowerShell": ("5391FE", "powershell", "white"),
    "Solidity": ("363636", "solidity", "white"),
    "Jupyter Notebook": ("F37626", "jupyter", "white"),
}


def fetch_repos():
    repos, page = [], 1
    while True:
        url = f"https://api.github.com/user/repos?affiliation=owner&per_page=100&page={page}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req) as r:
            batch = json.load(r)
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1


def esc(text):
    """Escapa texto para la ruta de un badge de shields.io."""
    return urllib.parse.quote(str(text).replace("-", "--").replace("_", "__").replace(" ", "_"))


def badge(label, value, color, logo="github", logo_color="white", alt=None):
    src = (f"https://img.shields.io/badge/{esc(label)}-{esc(value)}-{color}"
           f"?style=for-the-badge&logo={logo}&logoColor={logo_color}")
    return f'  <img src="{src}" alt="{alt or f"{label}: {value}"}">'


def build_block(repos):
    now = datetime.now(timezone.utc)
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    private = sum(r["private"] for r in repos)
    public = len(repos) - private
    active = sum(parse(r["pushed_at"]) >= now - timedelta(days=30) for r in repos if r["pushed_at"])
    new = sum(parse(r["created_at"]).year == now.year for r in repos)
    langs = Counter(r["language"] for r in repos if r["language"]).most_common(6)

    row1 = [
        badge("Proyectos totales", len(repos), "059669"),
        badge("Proyectos privados", private, "064e3b"),
        badge("Proyectos públicos", public, "10b981"),
    ]
    row2 = [
        badge("Activos últimos 30 días", active, "047857", logo="githubactions"),
        badge(f"Nuevos en {now.year}", new, "34d399", logo="git", logo_color="black"),
    ]
    row3 = []
    for name, n in langs:
        color, logo, lc = LANG_COLORS.get(name, ("374151", "github", "white"))
        row3.append(badge(name, f"{n} {'repo' if n == 1 else 'repos'}", color, logo, lc))

    p = lambda rows: '<p align="center">\n' + "\n".join(rows) + "\n</p>"
    return "\n".join([
        "<!-- REPO-COUNT:START -->",
        p(row1),
        p(row2),
        p(row3),
        f'<p align="center"><sub>Actualizado automáticamente el {now:%Y-%m-%d}</sub></p>',
        "<!-- REPO-COUNT:END -->",
    ])


def main():
    block = build_block(fetch_repos())
    text = open(README, encoding="utf-8").read()
    pattern = re.compile(r"<!-- REPO-COUNT:START -->.*?<!-- REPO-COUNT:END -->", re.S)
    if not pattern.search(text):
        sys.exit("No se encontró el bloque REPO-COUNT en el README")
    new_text = pattern.sub(lambda _: block, text)
    # La fecha cambia cada día; solo se guarda si cambió algo más.
    strip = lambda s: re.sub(r"Actualizado automáticamente el [0-9-]+", "", s)
    if strip(new_text) != strip(text) or "Actualizado automáticamente" not in text:
        open(README, "w", encoding="utf-8", newline="\n").write(new_text)
    print(block)


if __name__ == "__main__":
    main()
