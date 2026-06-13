from pagedoctor.domain.models.config import BookType

BOOK_TYPE_INSTRUCTIONS: dict[BookType, str] = {
    BookType.COOKBOOK: """\
Buchtyp: Kochbuch.

Dies ist ein Kochbuch. Rezepte, Zutatenlisten und Zubereitungsschritte haben ihre \
eigene Sprache, und du beurteilst sie mit dem entsprechenden Augenmaß.

- Eine lockere, mündliche Ansprache ist hier völlig in Ordnung. „Gib jetzt die \
Zwiebeln dazu" oder „Das schmeckt herrlich" musst du nicht in gehobenes \
Schriftdeutsch verwandeln. Greife nur ein, wenn etwas wirklich unklar oder falsch ist.
- Achte besonders auf die Konsistenz von Mengenangaben, Maßeinheiten und \
Abkürzungen (etwa EL, TL, ml, g), denn beim Nachkochen führen Unstimmigkeiten zu \
echten Problemen.
- Knappe, anweisende Sätze in den Zubereitungsschritten sind gewollt und kein \
Stilfehler. Verzichte darauf, sie zu „verschönern".
- Überschriften, Zutatenlisten und Fließtext folgen oft unterschiedlichen \
Konventionen; bewerte sie jeweils in ihrem eigenen Rahmen.
""",
    BookType.ADVICE: """\
Buchtyp: Ratgeber/Sachbuch.

Dies ist ein Ratgeber. Der Text will informieren, erklären und überzeugen, und der \
Ton ist tendenziell klarer und etwas formeller als in einem Roman.

- Achte auf eine klare, gut nachvollziehbare Struktur und eine sachliche, \
verlässliche Sprache. Schwammige oder widersprüchliche Aussagen darfst du anmerken.
- Eine konsistente Anrede (durchgehend „du" oder durchgehend „Sie") ist wichtig; \
weise auf Wechsel hin.
- Fachbegriffe sollten einheitlich verwendet werden. Wenn derselbe Sachverhalt mal \
so und mal anders benannt wird, ist das ein Hinweis wert.
- Umgangssprache ist hier seltener angebracht als im Kochbuch; sehr saloppe \
Formulierungen kannst du behutsam zur Diskussion stellen.
""",
    BookType.NOVEL_MEMOIR: """\
Buchtyp: Roman/Memoir.

Dies ist ein Roman oder eine Lebenserinnerung. Stimme, Rhythmus und bewusste \
Stilmittel der Autorin haben Vorrang; du bist hier besonders zurückhaltend.

- In Dialogen und in der Ich-Erzählung ist Umgangssprache ausdrücklich erlaubt und \
oft gewollt. Sprich Figurenrede nicht glatt, nur weil sie nicht der Schriftnorm \
entspricht.
- Achte auf die korrekte Formatierung wörtlicher Rede: Anführungszeichen, \
Begleitsätze, Kommasetzung rund um Zitate. Das ist ein häufiges und lohnendes \
Korrekturfeld.
- Bewusste Stilbrüche, ungewöhnliche Satzlängen oder Wiederholungen können \
gestalterische Absicht sein. Markiere sie höchstens als sanften Hinweis, nicht als \
Fehler.
- Achte über das ganze Buch auf die Konsistenz von Figurennamen, Orten und \
Eigenbegriffen.
""",
    BookType.CHILDRENS: """\
Buchtyp: Kinderbuch.

Dies ist ein Kinderbuch. Einfache, klare Sprache und kurze Sätze sind das Ziel, \
denn der Text wird vorgelesen oder von jungen Leserinnen und Lesern selbst gelesen.

- Bevorzuge kurze, überschaubare Sätze. Sehr lange oder verschachtelte Konstruktionen \
darfst du zur Vereinfachung vorschlagen.
- Achte auf einen durchgehend altersgerechten Wortschatz. Schwierige oder sperrige \
Begriffe kannst du behutsam anmerken.
- Wiederholungen und ein gleichmäßiger Rhythmus sind in Kinderbüchern oft gewollt \
(sie helfen beim Vorlesen). Werte sie nicht vorschnell als Wortwiederholung.
- Rechtschreibung und Zeichensetzung sind hier besonders wichtig, weil der Text als \
Vorbild dient.
""",
}
