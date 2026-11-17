"""Arma el documento del proyecto (DOCX) con las cifras reales del notebook."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diccionario import PRINCIPALES, OTRAS
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = "/home/user/Polymarket-UP-DOWN-5m/proyecto_enoe/"
R = json.load(open(ROOT + "resultados/resumen.json"))
FIG = ROOT + "figuras/"
M = R["modelos"]
RS = R["resumen"]
HIP = {h["Hipótesis"][:2]: h for h in R["hipotesis"]}

doc = Document()
sec = doc.sections[0]
sec.left_margin = sec.right_margin = Inches(1)
sec.top_margin = sec.bottom_margin = Inches(0.9)

estilo = doc.styles["Normal"]
estilo.font.name = "Times New Roman"
estilo.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
estilo.font.size = Pt(11.5)
estilo.paragraph_format.space_after = Pt(6)
estilo.paragraph_format.line_spacing = 1.25

n_tabla = [0]
n_fig = [0]


def f(x, d=3):
    return format(x, "." + str(d) + "f")


def miles(x):
    return format(int(round(x)), ",")


def pct(x, d=1):
    return f(x * 100, d) + "%"


def p(texto="", negrita=False, cursiva=False, centrado=False, tam=None, justificado=True, espacio=None):
    par = doc.add_paragraph()
    if centrado:
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif justificado:
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if espacio is not None:
        par.paragraph_format.space_after = Pt(espacio)
    r = par.add_run(texto)
    r.bold, r.italic = negrita, cursiva
    if tam:
        r.font.size = Pt(tam)
    return par


def mixto(partes):
    """Parrafo con partes en negrita: lista de (texto, negrita)."""
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for t, b in partes:
        r = par.add_run(t)
        r.bold = b
    return par


def h1(t):
    par = doc.add_paragraph()
    par.paragraph_format.space_before = Pt(14)
    par.paragraph_format.keep_with_next = True
    r = par.add_run(t)
    r.bold = True
    r.font.size = Pt(14)


def h2(t):
    par = doc.add_paragraph()
    par.paragraph_format.space_before = Pt(8)
    par.paragraph_format.keep_with_next = True
    r = par.add_run(t)
    r.bold = True
    r.font.size = Pt(12)


def lista(items, numerada=False):
    for i, t in enumerate(items):
        par = doc.add_paragraph(style="List Bullet" if not numerada else None)
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        par.paragraph_format.space_after = Pt(3)
        if numerada:
            par.paragraph_format.left_indent = Inches(0.3)
            par.paragraph_format.first_line_indent = Inches(-0.25)
            par.add_run(str(i + 1) + ".  ")
        if isinstance(t, tuple):
            r = par.add_run(t[0]); r.bold = True
            par.add_run(t[1])
        else:
            par.add_run(t)


def codigo(texto):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    celda = t.rows[0].cells[0]
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), "F0F0F0")
    celda._tc.get_or_add_tcPr().append(sh)
    celda.paragraphs[0].text = ""
    for i, linea in enumerate(texto.strip("\n").split("\n")):
        par = celda.paragraphs[0] if i == 0 else celda.add_paragraph()
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.line_spacing = 1.0
        r = par.add_run(linea)
        r.font.name = "Courier New"
        r.font.size = Pt(8.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def tabla(titulo, encabezados, filas, anchos=None, tam=9.5, izq=(0,)):
    n_tabla[0] += 1
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.keep_with_next = True
    r = par.add_run("Tabla " + str(n_tabla[0]) + ". " + titulo)
    r.italic = True
    r.font.size = Pt(10)
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, e in enumerate(encabezados):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(e)
        run.bold = True
        run.font.size = Pt(tam)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), "E5E7EB")
        c._tc.get_or_add_tcPr().append(sh)
    for fila in filas:
        cel = t.add_row().cells
        for i, v in enumerate(fila):
            cel[i].text = ""
            run = cel[i].paragraphs[0].add_run(str(v))
            run.font.size = Pt(tam)
            cel[i].paragraphs[0].paragraph_format.space_after = Pt(0)
            if i not in izq:
                cel[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if anchos:
        for fila in t.rows:
            for i, a in enumerate(anchos):
                fila.cells[i].width = Inches(a)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def figura(archivo, pie, ancho=5.8):
    n_fig[0] += 1
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.keep_with_next = True
    par.add_run().add_picture(FIG + archivo + ".png", width=Inches(ancho))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run("Figura " + str(n_fig[0]) + ". " + pie)
    r.italic = True
    r.font.size = Pt(10)


def que_hace(texto):
    mixto([("¿Qué hace este paso? ", True), (texto, False)])


def resultado(texto):
    mixto([("¿Qué resultado obtuve y qué significa? ", True), (texto, False)])


# ───────────────────────────── PORTADA ─────────────────────────────
par_logo = doc.add_paragraph()
par_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
par_logo.paragraph_format.space_before = Pt(30)
par_logo.add_run().add_picture(FIG + "logo_cugdl_negro.png", width=Inches(3.2))
for _ in range(4):
    doc.add_paragraph()
p("¿Quién trabaja en la informalidad? Predicción con datos de la ENOE (INEGI)", negrita=True, centrado=True, tam=18)
p("Proyecto integrador · Análisis de datos (tema libre)", cursiva=True, centrado=True, tam=12)
p("Analítica Predictiva", negrita=True, centrado=True, tam=13)
p("17 de noviembre de 2026", centrado=True, tam=12)
for _ in range(4):
    doc.add_paragraph()
mixto([("Objetivo: ", True), ("Explicar con mis palabras cada paso del proyecto (de dónde salen los datos, cómo los limpié, qué modelos "
                                "usé y qué resultados obtuve), interpretar las tablas y gráficas, y responder las preguntas de la rúbrica.", False)])
for _ in range(2):
    doc.add_paragraph()
p("Autora: Melany Liliana Santillan Salazar", centrado=True, negrita=True)
p("Profesor: Marco Antonio Cisneros Guevara", centrado=True, negrita=True)
doc.add_page_break()

# ───────────────────────────── RESUMEN / MAPA ─────────────────────────────
h1("Resumen del proyecto")
p("En este proyecto uso la Encuesta Nacional de Ocupación y Empleo (ENOE) del INEGI, del segundo trimestre de 2026, para predecir si una "
  "persona que trabaja tiene un empleo informal o formal. Trabajé con " + miles(R["n_estudio"]) + " personas ocupadas. Probé tres modelos "
  "(regresión logística, árbol de decisión y Random Forest) y el mejor fue el Random Forest, con un ROC-AUC de " + f(RS["auc_test"]) +
  " en los datos de prueba. Las variables que más ayudan a predecir son la escolaridad, las horas trabajadas y el ingreso. "
  "También encontré que si uno usa variables que ya definen la informalidad (como el acceso a seguridad social) el modelo parece "
  "perfecto, pero eso es trampa, por eso las dejé fuera.")
tabla("Datos y parámetros principales del proyecto", ["Concepto", "Valor"], [
    ["Fuente de datos", "INEGI – ENOE, 2.º trimestre 2026 (tabla SDEM)"],
    ["Registros / variables (base original)", miles(R["n_registros"]) + " / " + str(R["n_variables"])],
    ["Población de estudio (ocupados de 15 años o más)", miles(R["n_estudio"])],
    ["Entrenamiento / prueba (80% / 20%)", miles(R["n_train"]) + " / " + miles(R["n_test"])],
    ["Variable objetivo", "Informal = 1, Formal = 0"],
    ["Semilla (random_state)", "42"],
    ["Validación cruzada", "5 pliegues (GridSearchCV)"],
    ["Mejor modelo", RS["mejor"]],
], anchos=[3.2, 3.2])

# ───────────────────────────── 0 ─────────────────────────────
h1("0. Planteamiento del problema, objetivos e hipótesis")
h2("0.1 Planteamiento del problema")
mixto([("¿Qué problema quiero analizar? ", True),
       ("La informalidad laboral. Una persona está en la informalidad cuando trabaja sin seguridad social, sin prestaciones y sin "
        "contrato estable. Quiero saber qué características tienen las personas que trabajan en la informalidad y si con esos datos se "
        "puede predecir quién está en ese grupo.", False)])
mixto([("¿Por qué es importante en la vida real? ", True),
       ("En la ENOE, ponderando con el factor de expansión, " + pct(R["tasa_pond"]) + " de las personas ocupadas está en la informalidad. "
        "Eso significa que más de la mitad de quienes trabajan no tiene acceso a servicios médicos por su trabajo, ni ahorro para el "
        "retiro, ni prestaciones. Si se sabe qué grupos son más vulnerables, se pueden dirigir mejor los programas de formalización, "
        "de seguridad social y de capacitación.", False)])
mixto([("¿Por qué usar análisis de datos? ", True),
       ("Porque la encuesta tiene cientos de miles de registros y muchas variables al mismo tiempo (edad, escolaridad, ingreso, lugar, "
        "sector, etc.). A simple vista no se puede saber cuáles pesan más. Con estadística y aprendizaje automático puedo medir cada "
        "relación, comparar modelos y comprobar con números si mis ideas son correctas.", False)])
h2("0.2 Objetivos")
mixto([("Objetivo general. ", True),
       ("Construir y comparar modelos de clasificación que predigan si una persona ocupada tiene un empleo informal (1) o formal (0).", False)])
p("Objetivos específicos:", negrita=True, espacio=2)
lista([
    "Documentar de dónde salen los datos y limpiarlos (códigos de “no especificado”, nulos, duplicados y valores atípicos).",
    "Elegir las variables predictoras, justificar por qué y revisar que ninguna cause “fuga de información”.",
    "Comparar 3 modelos (regresión logística, árbol de decisión y Random Forest) usando validación cruzada de 5 pliegues.",
    "Lograr un ROC-AUC de al menos 0.80 en los datos de prueba, con una diferencia entre entrenamiento y prueba menor a 0.05.",
    "Explicar qué variables influyen más y comprobar las tres hipótesis.",
], numerada=True)
mixto([("¿Los objetivos son claros, medibles y congruentes? ", True),
       ("Sí: cada uno tiene un producto que se puede revisar (una tabla, una gráfica o una métrica con un número) y todos responden "
        "al problema de entender y predecir la informalidad.", False)])
h2("0.3 Hipótesis")
lista([
    ("H1 (escolaridad): ", "a más años de escuela, menor probabilidad de estar en la informalidad."),
    ("H2 (localidad): ", "vivir en una localidad de menos de 2,500 habitantes aumenta la probabilidad de informalidad, comparado con una ciudad de más de 100 mil habitantes."),
    ("H3 (ingreso): ", "a mayor ingreso por trabajo, menor probabilidad de informalidad."),
])
mixto([("¿Cómo las voy a contrastar? ", True),
       ("Con porcentajes por grupo, pruebas estadísticas (correlación de Spearman, chi cuadrada y t de Student) y las razones de momios "
        "(odds ratio) de la regresión logística. ", False),
       ("¿Qué resultados las respaldan o las rechazan? ", True),
       ("Una hipótesis se respalda si la diferencia va en la dirección esperada, la prueba tiene p < 0.05 y el odds ratio del modelo "
        "también va en esa dirección. Si algo de eso falla, la rechazo.", False)])

# ───────────────────────────── 1 ─────────────────────────────
h1("1. Procedencia y adquisición de la base de datos")
mixto([("¿Cuál es la fuente original? ", True),
       ("El INEGI, en su programa Encuesta Nacional de Ocupación y Empleo (ENOE), población de 15 años y más. Descargué el conjunto de "
        "datos abiertos del segundo trimestre de 2026 (https://www.inegi.org.mx/programas/enoe/15ymas/). No usé Kaggle.", False)])
mixto([("¿Hice trabajo de campo, encuestas o web scraping? ", True),
       ("No. Consulté un repositorio oficial: el INEGI levanta la encuesta y yo solo descargué el archivo público (un .zip de unos 41 MB) "
        "desde Python. De ahí tomé la tabla SDEM (características sociodemográficas y laborales).", False)])
mixto([("¿Por qué elegí esta fuente? ", True),
       ("Porque es la fuente oficial para medir empleo e informalidad en México, trae diccionario de datos y catálogos para entender cada "
        "variable, y tiene un tamaño suficiente para entrenar modelos.", False)])
mixto([("¿Cuántos registros y variables tiene? ", True),
       ("La base original tiene " + miles(R["n_registros"]) + " registros (personas) y " + str(R["n_variables"]) + " variables.", False)])
mixto([("¿Por qué los datos son confiables, pertinentes y suficientes? ", True),
       ("Son confiables porque los publica el INEGI con un diseño de muestra oficial. Son pertinentes porque la variable emp_ppal es la "
        "medición oficial de informalidad. Son suficientes porque hay cientos de miles de registros. Además hice una comprobación: con el "
        "factor de expansión la tasa de informalidad me dio " + pct(R["tasa_pond"]) + ", que es parecida a la que publica INEGI.", False)])
que_hace("Descarga el zip, extrae la tabla SDEM, la lee con pandas y convierte a número las columnas que voy a usar. Después filtra la "
         "población de estudio: personas ocupadas (clase2 = 1), de 15 años o más y clasificadas como formal o informal (emp_ppal = 1 o 2).")
codigo('''datos = pd.read_csv(BASE + "/conjunto_de_datos/conjunto_de_datos_sdem_enoe_2026_2t.csv",
                    encoding="latin1", low_memory=False)
d = datos[(datos["eda"] >= 15) & (datos["eda"] <= 98) &
          (datos["clase2"] == 1) & (datos["emp_ppal"].isin([1, 2]))].copy()
d["y"] = (d["emp_ppal"] == 1).astype(int)       # 1 = informal, 0 = formal''')
resultado("De " + miles(R["n_registros"]) + " registros quedaron " + miles(R["n_estudio"]) + " personas ocupadas con clasificación formal/informal. "
          "En la muestra, " + pct(R["tasa_muestra"]) + " son informales (sin ponderar); con el factor de expansión sube a " + pct(R["tasa_pond"]) +
          ". Para el modelo uso la muestra sin ponderar. Esto significa que las clases están casi balanceadas.")
figura("f01_embudo", "De la base completa a la población de estudio.", 5.4)

# ───────────────────────────── 2 ─────────────────────────────
h1("2. Limpieza y preprocesamiento de datos")
h2("2.1 Problemas de calidad que identifiqué")
que_hace("Revisa cada variable contra el diccionario de datos del INEGI. En la ENOE casi no hay celdas vacías, pero los datos que faltan "
         "están escritos como códigos (por ejemplo 99 = “no especificado”). Si no los detecto, el modelo los tomaría como números reales.")
filas = [[a["Variable"], a["Problema"], miles(a["Registros"]), f(a["% de la población"], 2) + "%"] for a in R["auditoria"]]
tabla("Problemas de calidad encontrados", ["Variable", "Problema", "Registros", "% de ocupados"], filas, anchos=[1.1, 2.7, 1.1, 1.3])
resultado("Los problemas más grandes son el ingreso igual a 0 (muchas personas no reciben pago o no lo declararon) y las horas igual a 0 "
          "(ausencia temporal del trabajo). El resto son pocos casos. Significa que no puedo usar el ingreso y las horas tal como vienen, "
          "tengo que tratar esos ceros y códigos primero.")
figura("f02_calidad", "Valores problemáticos por variable (% de ocupados).", 5.0)

h2("2.2 Nulos, duplicados e inconsistencias: ¿qué hice?")
lista([
    ("Duplicados: ", "usé duplicated() para buscar filas repetidas. Encontré " + str(R["duplicados"]) + " filas duplicadas, así que no hubo que eliminar nada."),
    ("Códigos de “no especificado”: ", "en anios_esc (99), e_con (9) y rama (7) los cambié por NaN."),
    ("Ingreso: ", "si ing7c = 7 (no especificado) lo puse como NaN. Si ing7c = 6 (no recibe ingresos) el cero sí es información real, por eso creé "
                  "la columna sin_ingreso (1 = sí, 0 = no)."),
    ("Horas: ", "hrsocup = 0 lo cambié a NaN."),
    ("Rellenar NaN: ", "en las numéricas usé la mediana del conjunto de entrenamiento; en las categóricas puse la categoría “No especificado”."),
])
codigo('''d["anios_esc"] = d["anios_esc"].where(d["anios_esc"] < 99)
d["hrsocup"] = d["hrsocup"].where(d["hrsocup"] > 0)
d["sin_ingreso"] = (d["ing7c"] == 6).astype(int)
d["ingreso"] = d["ingocup"].where(d["ing7c"] != 7)''')
p("Usé la mediana y no la media porque la mediana casi no cambia con valores extremos (por ejemplo, ingresos muy altos).")

h2("2.3 Valores atípicos (outliers)")
que_hace("Detecta los valores muy alejados con la regla del IQR (es atípico lo que pasa de Q3 + 1.5 × IQR) y luego los controla. Para el "
         "ingreso uso winsorización (limitar al percentil 99) y logaritmo; para las horas también limito al percentil 99. No elimino filas. Las horas las muestro con un histograma.")
at = R["atipicos"]
tabla("Valores atípicos detectados con la regla del IQR", ["Variable", "Límite IQR", "Atípicos", "% del total"], [
    ["Ingreso mensual", "$" + miles(at["ingreso"]["limite"]), miles(at["ingreso"]["n_atipicos"]), f(at["ingreso"]["porcentaje"], 2) + "%"],
    ["Horas por semana", f(at["hrsocup"]["limite"], 0), miles(at["hrsocup"]["n_atipicos"]), f(at["hrsocup"]["porcentaje"], 2) + "%"],
    ["Edad", f(at["eda"]["limite"], 0), miles(at["eda"]["n_atipicos"]), f(at["eda"]["porcentaje"], 2) + "%"],
], anchos=[2.0, 1.4, 1.4, 1.4])
resultado("Hay pocos atípicos (menos del 3% en todas las variables). El ingreso tiene una cola muy larga hacia la derecha, por eso el tope del "
          "percentil 99 quedó en $" + miles(R["topes"]["ingreso"]) + " y el de las horas en " + miles(R["topes"]["horas"]) + " por semana. "
          "En el histograma de horas se ve que casi todos trabajan jornadas de 40 a 48 horas (la barra más alta) y que hay una cola a la derecha con pocas personas que trabajan muchas horas; la línea roja es el tope. "
          "Significa que unos pocos valores extremos no van a dominar al modelo, y no perdí ninguna fila. La edad no la modifiqué porque "
          "los valores altos son personas mayores reales.")
figura("f03_outliers", "Ingreso original, ingreso limitado con logaritmo e histograma de las horas trabajadas.", 6.2)

h2("2.4 Variables cualitativas a cuantitativas, división y estandarización")
lista([
    ("Cualitativas a números: ", "usé One-Hot Encoding con pd.get_dummies(). Cada categoría se vuelve una columna de 0 y 1. Usé drop_first=True "
                                  "para quitar una categoría por variable y no repetir información. Lo apliqué a sexo, estado civil, tamaño de localidad, sector y estado."),
    ("División: ", "80% para entrenar y 20% para probar, con stratify para mantener la misma proporción de informales en las dos partes."),
    ("Estandarización: ", "con StandardScaler dejé las numéricas con media 0 y desviación 1, pero solo para la regresión logística. Esto es porque la "
                          "regresión logística es sensible a la escala (una variable en miles de pesos pesaría más que la edad). Los árboles no la necesitan, "
                          "porque solo comparan valores contra umbrales."),
    ("Sin fuga: ", "la mediana, el percentil 99 y el escalador los calculé solo con entrenamiento y después los apliqué a prueba, para que la prueba "
                   "sea como datos nuevos."),
])
codigo('''X = pd.get_dummies(X, columns=categoricas, drop_first=True, dtype=int)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2,
                                                    stratify=y, random_state=42)
escalador = StandardScaler()
X_train_esc[numericas] = escalador.fit_transform(X_train[numericas])
X_test_esc[numericas] = escalador.transform(X_test[numericas])''')
resultado("Quedaron " + miles(R["n_train"]) + " personas para entrenar y " + miles(R["n_test"]) + " para probar. El " + pct(R["balance"]["Informal"] / 100) +
          " del entrenamiento es informal, casi igual que en prueba. Las columnas pasaron de las originales a un conjunto de columnas numéricas y "
          "de 0/1 sin ningún nulo.")

h2("2.5 Base original vs. base procesada y verificación")
que_hace("Compara la media, la mediana y la correlación con la variable objetivo antes y después de limpiar, para comprobar que mis cambios "
         "no deformaron la información.")
vf = R["verificacion"]
tabla("Comparación antes y después de la limpieza (entrenamiento)", ["Variable", "Media antes", "Media después", "Mediana antes", "Mediana después", "Corr. y antes", "Corr. y después"],
      [[v["Variable"], f(v["Media antes"], 2), f(v["Media después"], 2), f(v["Mediana antes"], 2), f(v["Mediana después"], 2),
        f(v["Corr. con y antes"], 3), f(v["Corr. con y después"], 3)] for v in vf], tam=9)
ov = R["orig_vs_proc"]
tabla("Base original vs. base procesada", ["Base", "Filas", "Columnas", "Valores nulos"],
      [[o[""], miles(o["Filas"]), o["Columnas"], miles(o["Valores nulos"])] for o in ov], anchos=[2.5, 1.2, 1.2, 1.5])
resultado("Las medias y medianas casi no cambiaron y las correlaciones con la variable objetivo quedaron prácticamente iguales (por ejemplo, "
          "escolaridad: " + f(vf[1]["Corr. con y antes"]) + " antes y " + f(vf[1]["Corr. con y después"]) + " después). El ingreso es el que más "
          "cambia, porque ahí sí hubo atípicos que limitar y muchos NaN que rellenar, pero la mediana se mantiene. Esto significa que la "
          "limpieza ordenó los datos sin alterar sus relaciones. La base original tiene " + str(R["n_variables"]) + " columnas y muchos valores especiales; la procesada "
          "solo tiene las variables elegidas, todas numéricas y sin nulos.")
figura("f04_antes_despues", "Distribuciones antes y después de la limpieza.", 6.4)

# ───────────────────────────── 3 ─────────────────────────────
h1("3. Identificación y clasificación de variables")
p("En la ENOE las variables tienen nombres cortos (por ejemplo sex, e_con, rama). En mi código algunas las renombré para entenderlas mejor. "
  "En la Tabla siguiente pongo el nombre que uso en mi código, el nombre original de la ENOE y qué significa cada una.")
tabla("Variables que uso en el modelo (diccionario de variables)", ["Nombre en mi código", "Nombre original ENOE", "Qué significa", "Tipo", "Valores"],
      [list(v) for v in PRINCIPALES], anchos=[0.95, 0.95, 2.2, 1.0, 1.5], tam=8.5, izq=(0, 1, 2, 4))
tabla("Otras variables que revisé pero no usé como predictoras", ["Variable", "Qué significa", "¿Por qué no la usé?"],
      [list(v) for v in OTRAS], anchos=[0.9, 3.5, 2.2], tam=8.5, izq=(0, 1, 2))
h2("3.1 ¿Existe relación entre las variables y la variable objetivo?")
que_hace("Primero calcula el porcentaje de informalidad en cada grupo (si cambia mucho entre grupos, hay relación). Después hace pruebas "
         "estadísticas: chi cuadrada para las cualitativas y t de Student para las numéricas, con una medida de qué tan fuerte es la relación.")
tr = R["tasas"]
resultado("La informalidad baja mucho con la escolaridad: " + f(tr["grupo_esc"]["0"], 1) + "% entre quienes no tienen escuela y " + f(tr["grupo_esc"]["17+"], 1) +
          "% entre quienes tienen 17 años o más de estudio. Por edad se ve una forma de “U”: los jóvenes de 15 a 19 años tienen " + f(tr["grupo_edad"]["15-19"], 1) +
          "%, los de 30 a 44 años están cerca de 45%, y los de 65 años o más suben a " + f(tr["grupo_edad"]["65+"], 1) + "%. En las localidades de menos de 2,500 habitantes la "
          "informalidad es " + f(tr["localidad"]["Menos de 2.5 mil"], 1) + "%, contra " + f(tr["localidad"]["Más de 100 mil"], 1) + "% en ciudades grandes. Por sector, el agropecuario ("
          + f(tr["sector"]["Agropecuario"], 1) + "%) y la construcción (" + f(tr["sector"]["Construcción"], 1) + "%) son los más informales. El sexo casi no marca diferencia ("
          + f(tr["sexo"]["Hombre"], 1) + "% hombres y " + f(tr["sexo"]["Mujer"], 1) + "% mujeres). Significa que las variables sí tienen relación con la informalidad, y la "
          "escolaridad es la más fuerte.")
figura("f05_tasas_grupo", "Porcentaje de informalidad por grupos (la línea naranja es el promedio general).", 6.4)
eh, eb = R["estados_altos"], R["estados_bajos"]
p("Por estado, los más informales son " + ", ".join(k + " (" + f(v, 1) + "%)" for k, v in eh.items()) + "; los menos informales son " +
  ", ".join(k + " (" + f(v, 1) + "%)" for k, v in eb.items()) + ". Es decir, hay una brecha muy grande entre el sur y el norte del país.")
figura("f06_entidades", "Porcentaje de ocupados en informalidad por estado.", 4.6)
pr = R["pruebas"]
tabla("Fuerza de la relación de cada variable con la informalidad", ["Variable", "Prueba", "Fuerza*", "p-value"],
      [[x["Variable"], x["Prueba"], f(x["Fuerza"], 3), "< 0.001" if x["p-value"] < 0.001 else f(x["p-value"], 3)] for x in pr], anchos=[1.8, 1.7, 1.3, 1.3])
p("*Para chi cuadrada es la V de Cramér (0 a 1); para t de Student es el tamaño del efecto d de Cohen. Entre más grande, más fuerte la relación.", cursiva=True, tam=9.5)
resultado("Todas tienen p-value menor a 0.05 (con tantos datos casi cualquier diferencia sale significativa), por eso es mejor fijarse en la fuerza. "
          "Las más fuertes son escolaridad, ingreso, horas trabajadas, sector y tamaño de localidad. Las más débiles son edad y sexo. Esto me sirve "
          "para saber que la escolaridad será una de las variables más importantes en los modelos.")
figura("f07_relacion", "Fuerza de la relación con la informalidad.", 4.6)

h2("3.2 Variables redundantes, irrelevantes o con fuga de información")
mixto([("Redundantes. ", True),
       ("niv_ins (nivel de instrucción) y cs_p13_1 (escolaridad) miden casi lo mismo que anios_esc: su correlación de Spearman con anios_esc es "
        + f(R["corr_redundantes"]["niv_ins"], 2) + " y " + f(R["corr_redundantes"]["cs_p13_1"], 2) + ". Si las incluyera todas el modelo tendría información repetida, "
        "así que dejé solo anios_esc. Algo parecido pasa con ur (urbano/rural) y el tamaño de localidad.", False)])
figura("f08_correlacion", "Correlación de Spearman entre las variables numéricas.", 4.2)
mixto([("Fuga de información (data leakage). ", True),
       ("INEGI define la informalidad usando el acceso a seguridad social (seg_soc), la posición en la ocupación (pos_ocu) y el tamaño de la "
        "unidad económica (emple7c). Si las pusiera como predictoras, el modelo ya conocería la respuesta. Lo comprobé con un árbol de decisión "
        "con y sin esas variables.", False)])
fg = R["fuga"]
tabla("ROC-AUC de un árbol de decisión con y sin variables de fuga", ["Variables usadas", "ROC-AUC en prueba"],
      [[k, f(v, 3)] for k, v in fg.items()], anchos=[4.2, 1.8])
resultado("Mi modelo sin variables de fuga tiene un AUC de " + f(list(fg.values())[0], 3) + ". Al agregar seg_soc sube a " + f(fg["+ seg_soc (seguridad social)"], 3) +
          " y con las tres variables llega a " + f(fg["+ las tres juntas"], 3) + ", casi perfecto. Eso no es buen modelo, es trampa: ya sabe la respuesta porque esas variables "
          "son parte de la definición. Por eso las excluí del modelo final. Así mi resultado sí sirve para predecir en casos donde no se conoce la seguridad social.")
figura("f09_fuga", "El AUC se dispara al incluir variables que definen la informalidad.", 5.4)

# ───────────────────────────── 4 ─────────────────────────────
h1("4. Modelos de aprendizaje automático")
mixto([("¿El problema es de clasificación, regresión o agrupamiento? ", True),
       ("Es de clasificación, porque quiero predecir una categoría (informal o formal), no un número ni grupos sin etiqueta.", False)])
mixto([("¿Qué modelos usé y por qué? ", True), ("", False)])
lista([
    ("Regresión logística: ", "es el modelo base. Es sencillo y sus coeficientes se pueden interpretar como razones de momios."),
    ("Árbol de decisión: ", "se entiende fácil porque son reglas del tipo “si… entonces…” y puede captar relaciones que no son líneas rectas."),
    ("Random Forest: ", "junta muchos árboles y promedia sus respuestas; suele dar mejores resultados y sobreajusta menos que un solo árbol."),
    ("Modelo base (Dummy): ", "siempre predice la clase más común. Sirve para comprobar que mis modelos sí aprenden algo."),
])
mixto([("¿Cómo dividí los datos? ", True),
       ("80% entrenamiento y 20% prueba, con stratify. Para elegir los parámetros usé GridSearchCV con validación cruzada de 5 pliegues, en una muestra de "
        "30,000 filas del entrenamiento para que no tardara tanto; luego entrené con todo el entrenamiento usando los mejores parámetros. La prueba la usé "
        "una sola vez, al final.", False)])
mixto([("¿Qué métricas usé? ", True),
       ("Accuracy (porcentaje de aciertos), precision (de los que dije informales, cuántos de verdad lo son), recall (de los informales reales, cuántos encontré), "
        "F1 (combina precision y recall) y ROC-AUC (qué tan bien separa a formales de informales sin depender de un umbral; 0.5 es azar y 1 es perfecto).", False)])
h2("4.1 Desbalance de clases")
cw = R["class_weight"]
resultado("Las clases están casi balanceadas: " + f(R["balance"]["Informal"], 1) + "% informales y " + f(R["balance"]["Formal"], 1) + "% formales, así que no tengo un problema grave de desbalance. "
          "Probé class_weight='balanced' en la regresión logística y casi no cambió: el F1 pasó de " + f(cw[0]["F1"], 3) + " a " + f(cw[1]["F1"], 3) + ". "
          "Por eso no usé ninguna técnica especial (como sobremuestreo).")
figura("f10_balance", "Distribución de la variable objetivo y efecto de class_weight.", 5.6)
h2("4.2 Resultados de los modelos")
que_hace("Para cada modelo busca los mejores parámetros con validación cruzada, entrena con todo el entrenamiento y evalúa en prueba.")
codigo('''busqueda = GridSearchCV(modelos_base[nombre], parametros[nombre], cv=5, scoring="roc_auc")
busqueda.fit(Xtr.loc[muestra], y_train.loc[muestra])
modelo = modelos_base[nombre].set_params(**busqueda.best_params_)
modelo.fit(Xtr, y_train)
prob = modelo.predict_proba(Xte)[:, 1]''')
mp = R["mejores_parametros"]
tabla("Mejores parámetros encontrados", ["Modelo", "Parámetros"],
      [[k, ", ".join(a + "=" + b for a, b in v.items())] for k, v in mp.items()], anchos=[1.9, 4.5])
nombres = ["Modelo base", "Regresión logística", "Árbol de decisión", "Random Forest"]
tabla("Métricas en los datos de prueba", ["Modelo", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC"],
      [[n] + [f(M[n][k], 3) for k in ["accuracy", "precision", "recall", "F1", "ROC-AUC"]] for n in nombres], anchos=[2.0, 0.9, 0.9, 0.8, 0.8, 0.9])
figura("f12_roc", "Curvas ROC de los modelos en los datos de prueba.", 4.4)
figura("f13_metricas", "Comparación de métricas por modelo.", 5.8)
h2("4.3 Sobreajuste, bajo rendimiento y elección del mejor modelo")
tabla("Diagnóstico de sobreajuste (ROC-AUC)", ["Modelo", "Entrenamiento", "Validación cruzada", "Prueba", "Diferencia train-test"],
      [[n, f(M[n]["AUC entrenamiento"], 3), f(M[n]["AUC validación"], 3), f(M[n]["ROC-AUC"], 3), f(M[n]["Diferencia train-test"], 3)] for n in nombres[1:]],
      anchos=[1.9, 1.2, 1.4, 0.9, 1.3])
resultado("El Random Forest fue el mejor: tiene el AUC de validación cruzada más alto (" + f(M["Random Forest"]["AUC validación"], 3) + ") y también el mejor en prueba (" +
          f(RS["auc_test"], 3) + "), con F1 de " + f(RS["f1"], 3) + " y accuracy de " + f(RS["accuracy"], 3) + ". Lo elegí con la validación cruzada y no con la prueba para no hacer trampa. "
          "La diferencia entre entrenamiento y prueba es de " + f(RS["diferencia"], 3) + ", muy por debajo de mi límite de 0.05, así que casi no hay sobreajuste. "
          "El modelo base solo acierta " + f(M["Modelo base"]["accuracy"], 3) + " (siempre dice “informal”) y su AUC es 0.5, por lo tanto los tres modelos sí aprenden. "
          "La regresión logística rinde menos (AUC " + f(M["Regresión logística"]["ROC-AUC"], 3) + "), seguramente porque asume relaciones en línea recta y aquí hay relaciones más "
          "complicadas, como la forma de “U” de la edad. Se cumple mi objetivo de AUC mayor o igual a 0.80 con los tres modelos.")
figura("f14_sobreajuste", "ROC-AUC en entrenamiento, validación cruzada y prueba.", 5.0)
cm = R["confusion"]
resultado("La matriz de confusión del Random Forest muestra " + miles(cm[0][0]) + " formales bien clasificados y " + miles(cm[1][1]) + " informales bien clasificados. "
          "Se equivoca en " + miles(cm[0][1]) + " casos (formales que dijo informales) y en " + miles(cm[1][0]) + " casos (informales que dijo formales). Significa que se le "
          "escapan más informales de los que clasifica mal como informales (recall " + f(RS["recall"], 2) + " contra precision " + f(RS["precision"], 2) + ").")
figura("f15_confusion", "Matriz de confusión del Random Forest en prueba.", 3.6)

# ───────────────────────────── 5 ─────────────────────────────
h1("5. Estructura, funcionamiento y eficiencia de los programas")
mixto([("¿Qué lenguaje y herramientas usé? ", True), ("Python en Google Colab (notebook .ipynb).", False)])
mixto([("¿Qué librerías usé y para qué sirve cada una?", True), ("", False)])
tabla("Librerías utilizadas", ["Librería", "Función"], [
    ["pandas", "Tablas de datos: leer el CSV, filtrar, limpiar y agrupar"],
    ["numpy", "Operaciones con números y arreglos (logaritmo, percentiles)"],
    ["matplotlib y seaborn", "Hacer las gráficas"],
    ["scipy.stats", "Pruebas estadísticas (chi cuadrada, t de Student, Spearman)"],
    ["scikit-learn", "Dividir datos, estandarizar, entrenar modelos, validación cruzada y métricas"],
    ["urllib y zipfile", "Descargar el archivo de INEGI y descomprimirlo"],
], anchos=[1.8, 4.6])
mixto([("¿Cómo está estructurado el programa? ", True), ("En 7 etapas:", False)])
lista([
    "Descargar y leer los datos del INEGI.",
    "Filtrar la población de estudio (ocupados de 15 años o más).",
    "Limpiar: códigos especiales, nulos, duplicados y atípicos.",
    "Convertir variables cualitativas (get_dummies) y dividir en entrenamiento y prueba.",
    "Estandarizar y rellenar nulos usando solo el entrenamiento.",
    "Buscar parámetros con GridSearchCV y entrenar los modelos.",
    "Evaluar con las métricas e interpretar los resultados.",
], numerada=True)
mixto([("Instrucciones y funciones más importantes. ", True), ("", False)])
lista([
    ("train_test_split(..., stratify=y): ", "divide los datos sin cambiar la proporción de informales y formales."),
    ("pd.get_dummies(): ", "convierte cada categoría en una columna de 0 y 1."),
    ("StandardScaler: ", "con fit_transform aprende la media y la desviación del entrenamiento y estandariza; en prueba solo se usa transform."),
    ("GridSearchCV(cv=5): ", "prueba todas las combinaciones de parámetros y las evalúa con validación cruzada de 5 pliegues."),
    ("fit() y predict_proba(): ", "entrenar el modelo y obtener la probabilidad de que una persona sea informal."),
    ("roc_auc_score(): ", "calcula el ROC-AUC."),
])
h2("5.1 Operaciones con mayor carga computacional")
tm = R["tiempos"]
tabla("Tiempos medidos por modelo (segundos)", ["Modelo", "Búsqueda de parámetros", "Entrenamiento final", "Predicción (10 mil filas)"],
      [[n, f(v["Búsqueda de parámetros (s)"], 1), f(v["Entrenamiento final (s)"], 1), f(v["Predicción por 10 mil filas (s)"], 3)] for n, v in tm.items()],
      anchos=[2.0, 1.6, 1.5, 1.6])
resultado("Lo que más tarda es la búsqueda de parámetros con validación cruzada, porque entrena el modelo muchas veces (cada combinación × 5 pliegues). "
          "El Random Forest es el más pesado (" + f(tm["Random Forest"]["Búsqueda de parámetros (s)"], 1) + " s la búsqueda) porque entrena 100 a 200 árboles. Predecir es rápido en todos. "
          "Por eso hice la búsqueda con solo 30,000 filas y no con todo el entrenamiento.")
figura("f16_tiempos", "Tiempo de cómputo por modelo.", 4.6)
h2("5.2 Complejidad temporal")
p("Uso n = número de filas, p = número de variables y T = número de árboles.")
tabla("Complejidad temporal teórica", ["Modelo", "Entrenamiento", "Predecir una fila"], [
    ["Regresión logística", "O(n · p · iteraciones)", "O(p)"],
    ["Árbol de decisión", "O(n · p · log n)", "O(profundidad)"],
    ["Random Forest", "O(T · n · p · log n)", "O(T · profundidad)"],
], anchos=[2.2, 2.4, 2.0])
es = R["escalamiento"]["pendientes"]
resultado("Para comprobarlo medí cuánto tarda cada modelo al entrenar con 5,000, 10,000, 20,000, 40,000 y todo el entrenamiento. En una gráfica log-log, la pendiente "
          "indica cómo crece el tiempo: cerca de 1 es crecimiento casi lineal. Me salió " + f(es["Random Forest"], 2) + " para Random Forest, " + f(es["Árbol de decisión"], 2) +
          " para el árbol y " + f(es["Regresión logística"], 2) + " para la regresión logística. Esto es consistente con la teoría (el tiempo crece más o menos proporcional a n, con "
          "un poco más por el log n). La medición de la regresión logística es la menos confiable, porque su tiempo depende de cuántas iteraciones necesita para converger y "
          "no solo del número de filas.")
figura("f17_escalamiento", "Cómo crece el tiempo de entrenamiento al aumentar los datos.", 4.6)
h2("5.3 Mejoras posibles y reproducibilidad")
lista([
    "Guardar el modelo entrenado con joblib para no volver a entrenar cada vez.",
    "Poner el código repetido en funciones (por ejemplo, una función de limpieza y otra de evaluación) para reutilizarlo y que sea más legible.",
    "Usar RandomizedSearchCV para probar menos combinaciones y gastar menos tiempo.",
    "Leer solo las columnas necesarias del CSV (usecols) y usar tipos de datos más pequeños para gastar menos memoria.",
    "Agregar comentarios y nombres de variables más claros.",
])
mixto([("¿El programa permite reproducir los resultados? ", True),
       ("Sí. Fijé random_state = 42 en la división de datos, en los modelos y en las muestras. Entrené el mejor modelo dos veces y las predicciones fueron idénticas "
        "(" + ("sí" if R["reproducible"] else "no") + " se reprodujeron). Además el notebook descarga los datos directo del INEGI, así que cualquiera puede correrlo desde cero en Colab.", False)])

# ───────────────────────────── 6 ─────────────────────────────
h1("6. Resultados, interpretación y conclusiones")
h2("6.1 ¿Qué variables importan más?")
que_hace("Calcula la importancia de variables del Random Forest (qué tanto ayuda cada variable a separar formales de informales). Como get_dummies partió las "
         "categorías en varias columnas, las sumé de nuevo por variable original.")
im = sorted(R["importancia"].items(), key=lambda x: -x[1])
resultado("Las variables más importantes son " + ", ".join(k + " (" + f(v, 3) + ")" for k, v in im[:4]) + ". Las menos importantes son sexo (" + f(R["importancia"]["sexo"], 3) +
          ") y estado civil (" + f(R["importancia"]["estado_civil"], 3) + "). Significa que lo que más separa a una persona informal de una formal es cuánta escuela tiene, "
          "cuántas horas trabaja, cuánto gana y en qué sector trabaja; el sexo casi no aporta.")
figura("f18_importancia", "Importancia de variables en el Random Forest.", 4.8)
h2("6.2 Razones de momios y contraste de hipótesis")
que_hace("Con la regresión logística, exp(coeficiente) es la razón de momios (OR). Si OR > 1 la variable aumenta la probabilidad de ser informal; si OR < 1 la disminuye. "
         "En las numéricas el OR es por cada aumento de una desviación estándar. En las categorías se compara contra la categoría que quitó drop_first (hombre, casado, "
         "localidad de 15 mil a 100 mil, sector agropecuario y Aguascalientes).")
OR = R["or"]
sel = ["anios_esc", "hrsocup", "eda", "ingreso", "sin_ingreso", "localidad_Menos de 2.5 mil", "localidad_Más de 100 mil", "sector_Manufactura", "sector_Construcción", "sexo_Mujer"]
tabla("Razones de momios de la regresión logística (variables seleccionadas)", ["Variable", "OR", "Interpretación"],
      [[v, f(OR[v]["OR"], 2), ("aumenta la informalidad" if OR[v]["OR"] > 1 else "disminuye la informalidad")] for v in sel], anchos=[2.6, 0.9, 2.6])
figura("f19_odds_ratios", "Razones de momios (rojo: aumenta la informalidad; verde: la disminuye).", 5.2)
h2("6.3 Resultado de las hipótesis")
tabla("Contraste de hipótesis", ["Hipótesis", "Prueba", "Estadístico", "p-value", "OR", "Veredicto"],
      [[h["Hipótesis"], h["Prueba"], f(h["Estadístico"], 2), "< 0.001" if h["p-value"] < 0.001 else f(h["p-value"], 3), f(h["OR"], 2), h["Veredicto"]] for h in R["hipotesis"]],
      anchos=[1.5, 1.0, 1.0, 0.8, 0.7, 1.2], tam=9)
lista([
    ("H1 (escolaridad) – " + HIP["H1"]["Veredicto"] + ". ", "La correlación de Spearman es " + f(HIP["H1"]["Estadístico"], 2) + " (negativa) y el OR es " + f(HIP["H1"]["OR"], 2) +
     ": por cada desviación estándar más de escolaridad, los momios de ser informal bajan a menos de la mitad. Es la variable más importante del Random Forest."),
    ("H2 (localidad) – " + HIP["H2"]["Veredicto"] + ". ", "En localidades de menos de 2,500 habitantes la informalidad es " + f(R["tasa_rural"], 1) + "% contra " + f(R["tasa_urbana"], 1) +
     "% en ciudades de más de 100 mil. La chi cuadrada es significativa y el OR contra las ciudades grandes es " + f(HIP["H2"]["OR"], 2) + "."),
    ("H3 (ingreso) – " + HIP["H3"]["Veredicto"] + ". ", "Aquí hay que explicar. Los informales ganan menos en promedio ($" + miles(R["ingreso_medio"]["informal"]) + " contra $" + miles(R["ingreso_medio"]["formal"]) +
     " mensuales) y la diferencia es significativa, pero en la regresión logística el OR del ingreso es " + f(HIP["H3"]["OR"], 2) + ", es decir, casi 1 y hasta con sentido contrario. "
     "Eso significa que el ingreso por sí solo no explica la informalidad una vez que ya se toman en cuenta la escolaridad, las horas y el sector: los informales ganan menos "
     "porque estudian menos y trabajan en sectores peor pagados. Por mi criterio (necesito que la prueba y el OR coincidan) la rechazo como efecto independiente, aunque "
     "el ingreso sí ayuda a predecir (es la tercera variable más importante del Random Forest)."),
])
h2("6.4 Respuestas a las preguntas del proyecto")
mixto([("¿Cuáles fueron los principales resultados? ", True),
       ("El Random Forest predice la informalidad con ROC-AUC de " + f(RS["auc_test"], 3) + ", accuracy de " + f(RS["accuracy"], 3) + " y F1 de " + f(RS["f1"], 3) + ". Es mejor que la regresión logística y el árbol.", False)])
mixto([("¿Qué patrones o relaciones identifiqué? ", True),
       ("Menos escolaridad, más informalidad; los muy jóvenes y los adultos mayores son más informales; las localidades pequeñas y el sector agropecuario y de construcción "
        "tienen más informalidad; el sur del país (Oaxaca, Tlaxcala, Guerrero) es más informal que el norte (Chihuahua, Coahuila, Baja California).", False)])
mixto([("¿Qué significan en el contexto del problema? ", True),
       ("Que la informalidad no se reparte al azar: está muy ligada a la educación y al lugar donde se vive. Por eso mejorar la educación y la oferta de empleo formal en "
        "localidades pequeñas sería una forma de reducirla.", False)])
mixto([("¿Se cumplieron los objetivos? ", True),
       ("Sí. Documenté y limpié los datos, revisé la fuga de información, comparé 3 modelos con validación cruzada, superé el AUC de 0.80 con una diferencia entre entrenamiento "
        "y prueba de solo " + f(RS["diferencia"], 3) + ", y expliqué las variables y las hipótesis.", False)])
mixto([("¿Qué evidencia respalda o rechaza las hipótesis? ", True),
       ("H1 y H2 se respaldan con las pruebas y el modelo; H3 se rechaza como efecto independiente (ver arriba).", False)])
h2("6.5 Limitaciones y trabajo futuro")
lista([
    "Usé un solo trimestre de la ENOE; sería mejor usar varios para ver cambios en el tiempo.",
    "No usé el factor de expansión en los modelos, por eso las probabilidades describen la muestra y no a toda la población.",
    "El modelo muestra relaciones, no causas: no puedo decir que más escuela cause menos informalidad, solo que van juntas.",
    "Dejé fuera a propósito las variables que definen la informalidad; con ellas el modelo sería casi perfecto pero no serviría.",
    "La búsqueda de parámetros se hizo en una muestra de 30,000 filas y con pocas combinaciones, así que quizás se puede mejorar un poco.",
    "Trabajo futuro: usar varios trimestres, ponderar con el factor de expansión, probar otros modelos (como gradient boosting) y agregar más variables.",
])
mixto([("¿Qué aportación concreta tiene el proyecto? ", True),
       ("Muestra con datos oficiales y recientes qué características se asocian a la informalidad, deja un programa que se puede reproducir y advierte del error de usar "
        "variables que ya definen la respuesta.", False)])
h1("7. Conclusiones")
lista([
    "La ENOE del 2.º trimestre de 2026 permitió estudiar " + miles(R["n_estudio"]) + " personas ocupadas; " + pct(R["tasa_pond"]) + " de ellas (ponderado) está en la informalidad.",
    "La limpieza fue importante: los datos faltantes venían como códigos (99, 9, 7) y los ceros de ingreso y horas necesitaban un tratamiento especial.",
    "Las variables que definen la informalidad (seguridad social, posición en la ocupación y tamaño de la unidad) causan fuga de información y se excluyeron.",
    "El Random Forest fue el mejor modelo (ROC-AUC " + f(RS["auc_test"], 3) + ") y casi no sobreajusta.",
    "La escolaridad, las horas trabajadas, el ingreso y el sector son las variables que más pesan.",
    "Se respaldan H1 y H2; H3 no se sostiene como efecto independiente del ingreso.",
    "Como alumna primeriza, lo que más aprendí fue a no confiar en un AUC demasiado bueno sin revisar primero si hay fuga de información.",
])
h1("Referencias")
for t in [
    "INEGI. (2026). Encuesta Nacional de Ocupación y Empleo (ENOE), población de 15 años y más de edad, 2.º trimestre de 2026. Conjunto de datos abiertos, tabla SDEM y diccionario de datos. https://www.inegi.org.mx/programas/enoe/15ymas/",
    "scikit-learn. (s. f.). Documentación de scikit-learn: model_selection, preprocessing, linear_model, tree y ensemble. https://scikit-learn.org/stable/",
    "pandas. (s. f.). pandas documentation. https://pandas.pydata.org/docs/",
    "SciPy. (s. f.). scipy.stats. https://docs.scipy.org/doc/scipy/reference/stats.html",
]:
    p(t, tam=10)

doc.save(ROOT + "Reporte_Proyecto_ENOE_Informalidad.docx")
print("reporte listo; tablas:", n_tabla[0], "figuras:", n_fig[0])
