from pagedoctor.domain.models.config import Strictness

STRICTNESS_INSTRUCTIONS: dict[Strictness, str] = {
    Strictness.LIGHT: """\
Strenge: leicht.

Bei dieser Einstellung meldest du ausschließlich echte Fehler. Halte dich bei \
allem Stilistischen zurück.

- Melde Rechtschreibfehler, Tippfehler und Buchstabendreher.
- Melde Grammatikfehler (Kasus, Kongruenz, Satzbau) und klare Verstöße bei der \
Pflicht-Kommasetzung.
- Melde eindeutig falsche Zeichensetzung.
- Melde KEINE Stilfragen, KEINE Wortwiederholungen und KEINE \
Lesbarkeitsempfehlungen, solange der Satz korrekt ist. Im Zweifel schweigst du.
- Fast alle Anmerkungen tragen hier die Priorität [FEHLER].
""",
    Strictness.STANDARD: """\
Strenge: normal.

Bei dieser Einstellung meldest du echte Fehler und zusätzlich die wichtigsten \
stilistischen Auffälligkeiten.

- Alles aus der leichten Stufe (Rechtschreibung, Grammatik, Zeichensetzung).
- Zusätzlich auffällige Wortwiederholungen und Füllwörter in unmittelbarer Nähe.
- Zusätzlich Unstimmigkeiten bei Begriffen, Namen und Schreibweisen.
- Klar holprige oder missverständliche Formulierungen darfst du als Empfehlung \
anmerken.
- Verwende die Prioritäten differenziert: [FEHLER] für echte Fehler, [EMPFEHLUNG] \
für sinnvolle Verbesserungen, [HINWEIS] sparsam für reine Geschmacksfragen.
""",
    Strictness.THOROUGH: """\
Strenge: gründlich.

Bei dieser Einstellung gehst du den Text umfassend durch und meldest auch feinere \
stilistische Punkte.

- Alles aus der normalen Stufe.
- Zusätzlich Lesbarkeit: sehr lange oder stark verschachtelte Sätze (Faustregel: \
deutlich über vierzig Wörter) darfst du zur Aufteilung vorschlagen.
- Zusätzlich Vorschläge für klarere oder elegantere Formulierungen, wo der Text \
gewinnt.
- Zusätzlich feinere Wiederholungen und Rhythmusfragen.
- Bleibe trotz der Gründlichkeit verhältnismäßig: Stilvorschläge sind [EMPFEHLUNG] \
oder [HINWEIS], niemals [FEHLER]. Die Stimme der Autorin bleibt maßgeblich.
""",
}
