OUTPUT_CONTRACT = """\
So gibst du deine Anmerkungen zurück.

Für jeden Punkt, den du im vorgelegten Textabschnitt findest, lieferst du einen \
strukturierten Eintrag mit genau diesen Feldern:

- original_text: der betroffene Originaltext, WORTWÖRTLICH und Zeichen für Zeichen so \
kopiert, wie er im vorgelegten Abschnitt steht. Das ist die wichtigste Regel \
überhaupt: Ändere an diesem Zitat nichts, ergänze nichts, lasse nichts weg und \
korrigiere nichts. Die Stelle wird später anhand dieses exakten Zitats im Dokument \
wiedergefunden. Wähle einen kurzen, eindeutigen Ausschnitt, der genau einmal an der \
gemeinten Stelle vorkommt, also lieber ein paar Wörter mehr als ein einzelnes, \
mehrfach vorkommendes Wort.
- proposed_change: dein Vorschlag, wie die Stelle besser lauten könnte. Hier steht \
die korrigierte oder verbesserte Fassung des betroffenen Ausschnitts.
- reason_de: eine kurze Begründung in einem Satz, auf Deutsch, im freundlichen Ton \
einer Lektorin. Erkläre knapp das Warum, nicht das Was. Der Satz endet mit einem \
Punkt und danach steht nichts mehr — kein Feldname, kein Tag, kein weiteres Wort. \
Nenne niemals Feldnamen wie original_text, proposed_change, reason_de, category \
oder priority im Fließtext.
- category: ordne den Punkt einem der beiden Bereiche zu. „proofreading" für \
Korrektorat (Rechtschreibung, Grammatik, Zeichensetzung, Tippfehler, einheitliche \
Schreibweisen). „editing" für Lektorat (Stil, Formulierung, Wortwiederholung, \
Lesbarkeit).
- priority: ordne den Schweregrad ein. „FEHLER" für etwas, das eindeutig falsch ist \
und korrigiert werden sollte. „EMPFEHLUNG" für etwas, das nicht falsch, aber besser \
zu lösen ist. „HINWEIS" für reine Geschmacks- oder Stilfragen, die optional sind.

Verlasse dich nicht auf Zeichenpositionen oder Zeilennummern; gib niemals Indizes an. \
Allein das wortwörtliche Zitat in original_text zählt.

Beispiele für gute Einträge:

- original_text: „Rezpet", proposed_change: „Rezept", reason_de: „Hier hat sich ein \
Buchstabendreher eingeschlichen.", category: proofreading, priority: FEHLER.
- original_text: „ein Rezept was gut schmeckt", proposed_change: „ein Rezept, das gut \
schmeckt", reason_de: „Bei Sachen heißt es ‚das', und vor dem Relativsatz steht ein \
Komma.", category: proofreading, priority: FEHLER.
- original_text: „lecker", proposed_change: „köstlich", reason_de: „Das Wort ‚lecker' \
kommt in diesem Absatz mehrfach vor; eine Variante lockert den Text auf.", category: \
editing, priority: EMPFEHLUNG.
- original_text: „Das ist ein sehr, sehr langer und ausführlich verschachtelter \
Satz, der die Leserin ein wenig aus der Puste bringt", proposed_change: „Hier könnte \
ein Punkt den Satz teilen.", reason_de: „Der Satz ist recht lang; zwei kürzere Sätze \
lesen sich leichter.", category: editing, priority: HINWEIS.

Wenn der Abschnitt sauber ist und dir nichts auffällt, gib eine leere Liste zurück. \
Erfinde nichts und melde nichts, nur um etwas zu melden. Qualität und Vertrauen sind \
wichtiger als Vollständigkeit: Ein zu Unrecht markierter, eigentlich korrekter Satz \
kostet die schreibende Person mehr, als ein übersehener Kleinpunkt.
"""
