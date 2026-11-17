"""Presentacion en blanco y negro con datos/importante en colores pastel (cifras reales del notebook)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diccionario import PRINCIPALES, OTRAS
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = "/home/user/Polymarket-UP-DOWN-5m/proyecto_enoe/"
R = json.load(open(ROOT + "resultados/resumen.json"))
FIGP = ROOT + "figuras_ppt/"      # graficas en colores pastel
FIG = ROOT + "figuras/"
M, RS = R["modelos"], R["resumen"]
HIP = {h["Hipótesis"][:2]: h for h in R["hipotesis"]}

# Blanco y negro + pastel
NEGRO = RGBColor(0x11, 0x11, 0x11)
TEXTO = RGBColor(0x1F, 0x1F, 0x1F)
GRIS = RGBColor(0x6B, 0x72, 0x80)
GRISC = RGBColor(0xF4, 0xF4, 0xF4)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
P_AZUL = RGBColor(0xBF, 0xD9, 0xF7)
P_DURAZNO = RGBColor(0xFB, 0xD3, 0xA8)
P_MENTA = RGBColor(0xBD, 0xE8, 0xCB)
P_LILA = RGBColor(0xD8, 0xC9, 0xF2)
P_ROSA = RGBColor(0xF8, 0xC4, 0xCC)
P_AMARILLO = RGBColor(0xFB, 0xEB, 0xA8)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
contador = [1]


def f(x, d=3):
    return format(x, "." + str(d) + "f")


def miles(x):
    return format(int(round(x)), ",")


def caja(s, x, y, w, h, relleno=None, borde=None, grosor=1.0):
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    if relleno is None:
        sh.fill.background()
    else:
        sh.fill.solid(); sh.fill.fore_color.rgb = relleno
    if borde is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = borde; sh.line.width = Pt(grosor)
    sh.shadow.inherit = False
    return sh


def texto(s, x, y, w, h, partes, tam=17, color=TEXTO, alinea=PP_ALIGN.LEFT, ancla=MSO_ANCHOR.TOP, espacio=6):
    """partes: lista de parrafos; cada parrafo es str o lista de (texto, negrita)."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = ancla
    tf.margin_left = tf.margin_right = Inches(0.06)
    for i, par in enumerate(partes):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = alinea
        p.space_after = Pt(espacio)
        if isinstance(par, str):
            par = [(par, False)]
        for t, b in par:
            r = p.add_run(); r.text = t
            r.font.size = Pt(tam); r.font.bold = b; r.font.color.rgb = color; r.font.name = "Calibri"
    return tb


def viñetas(s, x, y, w, h, items, tam=17, espacio=7):
    partes = []
    for it in items:
        if isinstance(it, tuple):
            partes.append([("▪  " + it[0], True), (it[1], False)])
        else:
            partes.append([("▪  " + it, False)])
    return texto(s, x, y, w, h, partes, tam=tam, espacio=espacio)


def callout(s, x, y, w, h, titulo, cuerpo, color=P_AMARILLO, tam=15):
    caja(s, x, y, w, h, color, NEGRO, 1.25)
    texto(s, x + 0.12, y + 0.05, w - 0.24, h - 0.1, [[(titulo + "  ", True), (cuerpo, False)]], tam=tam, ancla=MSO_ANCHOR.MIDDLE)


def dato(s, x, y, w, numero, etiqueta, color=P_AZUL, h=1.35):
    caja(s, x, y, w, h, color, NEGRO, 1.25)
    texto(s, x + 0.15, y + 0.05, w - 0.3, 0.75, [[(numero, True)]], tam=30)
    texto(s, x + 0.15, y + 0.75, w - 0.3, h - 0.8, [etiqueta], tam=13)


def nueva(titulo, notas=""):
    s = prs.slides.add_slide(BLANK)
    contador[0] += 1
    caja(s, 0, 0, 13.333, 1.0, NEGRO)
    s.shapes.add_picture(FIG + "logo_cugdl_blanco.png", Inches(11.35), Inches(0.2), width=Inches(1.75))
    texto(s, 0.5, 0.1, 10.7, 0.8, [[(titulo, True)]], tam=28, color=BLANCO, ancla=MSO_ANCHOR.MIDDLE)
    caja(s, 0, 1.0, 13.333, 0.06, P_DURAZNO)
    texto(s, 0.5, 7.08, 9, 0.3, ["Melany Liliana Santillan Salazar · Analítica Predictiva · Prof. Marco Antonio Cisneros Guevara"], tam=10, color=GRIS)
    texto(s, 12.0, 7.08, 1.0, 0.3, [str(contador[0])], tam=10, color=GRIS, alinea=PP_ALIGN.RIGHT)
    if notas:
        s.notes_slide.notes_text_frame.text = notas
    return s


def imagen(s, nombre, x, y, maxw, maxh, pastel=True, borde=True):
    ruta = (FIGP if pastel and os.path.exists(FIGP + nombre + ".png") else FIG) + nombre + ".png"
    w0, h0 = Image.open(ruta).size
    esc = min(maxw / w0, maxh / h0)
    w, h = w0 * esc, h0 * esc
    xx = x + (maxw - w) / 2
    pic = s.shapes.add_picture(ruta, Inches(xx), Inches(y), width=Inches(w), height=Inches(h))
    if borde:
        pic.line.color.rgb = NEGRO; pic.line.width = Pt(0.75)
    return pic


def tabla(s, x, y, w, filas, anchos, tam=14, alto=0.42, izq=(0,), colores=None):
    """colores: dict {(fila, col): RGBColor} para resaltar celdas importantes en pastel."""
    colores = colores or {}
    nf, nc = len(filas), len(filas[0])
    t = s.shapes.add_table(nf, nc, Inches(x), Inches(y), Inches(w), Inches(alto * nf)).table
    for j, a in enumerate(anchos):
        t.columns[j].width = Inches(a)
    for i, fila in enumerate(filas):
        for j, v in enumerate(fila):
            c = t.cell(i, j)
            c.text = str(v)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            para = c.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.LEFT if j in izq else PP_ALIGN.CENTER
            for r in para.runs:
                r.font.size = Pt(tam); r.font.name = "Calibri"
                r.font.bold = (i == 0) or ((i, j) in colores)
                r.font.color.rgb = BLANCO if i == 0 else TEXTO
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = NEGRO
            elif (i, j) in colores:
                c.fill.fore_color.rgb = colores[(i, j)]
            else:
                c.fill.fore_color.rgb = GRISC if i % 2 == 0 else BLANCO
    return t


# ═════════ 1 Portada ═════════
s = prs.slides.add_slide(BLANK)
caja(s, 0, 0, 13.333, 7.5, NEGRO)
s.shapes.add_picture(FIG + "logo_cugdl_blanco.png", Inches(0.8), Inches(0.5), width=Inches(3.4))
texto(s, 0.8, 1.7, 11.7, 2.0, [[("¿Quién trabaja en la informalidad?", True)], [("Predicción con datos de la ENOE (INEGI)", True)]], tam=40, color=BLANCO)
caja(s, 0.8, 3.75, 2.2, 0.09, P_DURAZNO)
caja(s, 3.1, 3.75, 1.2, 0.09, P_AZUL)
caja(s, 4.4, 3.75, 0.8, 0.09, P_MENTA)
texto(s, 0.8, 4.0, 11.7, 0.6, ["Proyecto integrador · Análisis de datos (tema libre)"], tam=22, color=P_AZUL)
texto(s, 0.8, 4.9, 11.7, 1.8, ["Alumna: Melany Liliana Santillan Salazar", "Materia: Analítica Predictiva",
                                "Profesor: Marco Antonio Cisneros Guevara", "Centro Universitario de Guadalajara · Noviembre de 2026"], tam=18, color=BLANCO)
s.notes_slide.notes_text_frame.text = ("Hola, buenas. Mi proyecto trata sobre la informalidad laboral en México. Usé datos oficiales del INEGI para ver qué características "
                                       "tienen las personas que trabajan en la informalidad y para armar modelos que la puedan predecir.")

# ═════════ 2 Ruta ═════════
s = nueva("¿Qué voy a mostrar?", "Esta es la ruta de mi presentación. Sigo las partes que pide la rúbrica, de la 0 a la 6.")
pasos = [("0", "Problema, objetivos e hipótesis", P_AZUL), ("1", "De dónde salen los datos", P_DURAZNO), ("2", "Limpieza y preprocesamiento", P_MENTA),
         ("3", "Variables y relación con la informalidad", P_LILA), ("4", "Modelos de aprendizaje automático", P_ROSA),
         ("5", "Estructura y eficiencia del programa", P_AMARILLO), ("6", "Resultados y conclusiones", P_AZUL)]
for i, (n, t, c) in enumerate(pasos):
    col, fila = i % 2, i // 2
    x, y = 0.6 + col * 6.3, 1.45 + fila * 1.35
    caja(s, x, y, 0.9, 1.1, c, NEGRO, 1.25)
    texto(s, x, y, 0.9, 1.1, [[(n, True)]], tam=32, alinea=PP_ALIGN.CENTER, ancla=MSO_ANCHOR.MIDDLE)
    caja(s, x + 0.9, y, 5.1, 1.1, BLANCO, NEGRO, 1.25)
    texto(s, x + 1.05, y, 4.9, 1.1, [t], tam=19, ancla=MSO_ANCHOR.MIDDLE)

# ═════════ 3 Problema ═════════
s = nueva("El problema: la informalidad laboral",
          "La informalidad es cuando alguien trabaja sin seguridad social, sin prestaciones y sin contrato estable. En México más de la mitad de quienes trabajan están así. "
          "Quise saber qué características tienen estas personas y si se pueden predecir con los datos.")
viñetas(s, 0.5, 1.35, 7.4, 4.0, [
    ("¿Qué es? ", "Trabajar sin seguridad social, sin prestaciones y sin contrato estable."),
    ("¿Por qué importa? ", "Quien está en la informalidad no tiene servicio médico por su trabajo ni ahorro para el retiro."),
    ("¿Por qué usar datos? ", "La encuesta tiene cientos de miles de personas; con tantos datos no se ve a simple vista qué pesa más, y para eso sirven los modelos."),
    ("Mi pregunta: ", "¿se puede predecir si una persona está en la informalidad con sus características?"),
], tam=18)
dato(s, 8.3, 1.4, 4.5, f(R["tasa_pond"] * 100, 1) + "%", "de las personas ocupadas está en la informalidad (dato ponderado con el factor de expansión)", P_ROSA)
dato(s, 8.3, 2.95, 4.5, miles(R["n_estudio"]), "personas ocupadas en mi población de estudio", P_AZUL)
dato(s, 8.3, 4.5, 4.5, "2.º trim. 2026", "ENOE del INEGI, fuente oficial", P_MENTA)
callout(s, 0.5, 5.6, 7.5, 1.2, "Idea clave:", "si se sabe qué grupos son más vulnerables, se pueden dirigir mejor los programas de formalización y seguridad social.")

# ═════════ 4 Objetivos e hipótesis ═════════
s = nueva("Objetivos e hipótesis", "Mi objetivo general es clasificar a las personas ocupadas en informales o formales. Plantee tres hipótesis para comprobar con los datos.")
caja(s, 0.5, 1.35, 6.1, 4.3, GRISC, NEGRO, 1)
texto(s, 0.7, 1.4, 5.7, 0.5, [[("Objetivos", True)]], tam=22)
viñetas(s, 0.7, 1.95, 5.7, 3.7, [
    ("General: ", "predecir si una persona ocupada es informal (1) o formal (0)."),
    "Limpiar los datos y revisar que no haya fuga de información.",
    "Comparar 3 modelos con validación cruzada.",
    "Lograr un ROC-AUC de al menos 0.80 en prueba.",
    "Explicar qué variables pesan más.",
], tam=16)
caja(s, 6.8, 1.35, 6.0, 4.3, GRISC, NEGRO, 1)
texto(s, 7.0, 1.4, 5.6, 0.5, [[("Hipótesis", True)]], tam=22)
for i, (h, t, c) in enumerate([("H1", "A más escolaridad, menos informalidad.", P_AZUL),
                               ("H2", "Vivir en una localidad de menos de 2,500 habitantes aumenta la informalidad.", P_DURAZNO),
                               ("H3", "A mayor ingreso, menos informalidad.", P_MENTA)]):
    y = 2.0 + i * 1.15
    caja(s, 7.0, y, 0.8, 1.0, c, NEGRO, 1)
    texto(s, 7.0, y, 0.8, 1.0, [[(h, True)]], tam=22, alinea=PP_ALIGN.CENTER, ancla=MSO_ANCHOR.MIDDLE)
    texto(s, 7.9, y, 4.8, 1.0, [t], tam=16, ancla=MSO_ANCHOR.MIDDLE)
callout(s, 0.5, 5.85, 12.3, 1.0, "¿Cómo las compruebo?", "Con porcentajes por grupo, pruebas estadísticas (p < 0.05) y el odds ratio de la regresión logística. Se respaldan si todo va en la dirección esperada.")

# ═════════ 5 Datos ═════════
s = nueva("Procedencia de los datos", "Descargué la base del sitio de datos abiertos del INEGI. No usé Kaggle, no hice encuestas ni web scraping.")
viñetas(s, 0.5, 1.35, 6.4, 4.3, [
    ("Fuente: ", "INEGI, Encuesta Nacional de Ocupación y Empleo (ENOE), 2.º trimestre 2026."),
    ("Cómo la obtuve: ", "descargué el zip (41 MB) del repositorio oficial de datos abiertos; uso la tabla SDEM."),
    ("Tamaño: ", miles(R["n_registros"]) + " registros (personas) y " + str(R["n_variables"]) + " variables."),
    ("Confiable: ", "muestra oficial, con diccionario de datos y catálogos públicos."),
], tam=17)
imagen(s, "f01_embudo", 7.1, 1.4, 5.8, 2.6)
texto(s, 7.1, 4.05, 5.8, 1.0, ["Me quedé con las personas ocupadas de 15 años o más que INEGI clasificó como formales o informales."], tam=14)
callout(s, 0.5, 5.8, 12.3, 1.05, "Comprobación:", "con el factor de expansión (cuántas personas representa cada registro) la informalidad da " +
        f(R["tasa_pond"] * 100, 1) + "%, parecida a la que publica INEGI. Sin ponderar es " + f(R["tasa_muestra"] * 100, 1) + "%.", P_MENTA)

# ═════════ 6 Diccionario ═════════
s = nueva("Diccionario de variables que uso", "En la ENOE las variables tienen nombres cortos. En mi código renombré algunas. Aquí explico cada una.")
filas = [["En mi código", "En la ENOE", "Qué significa"]] + [[v[0], v[1], v[2]] for v in PRINCIPALES]
col = {(1, 0): P_ROSA, (1, 1): P_ROSA, (1, 2): P_ROSA}
tabla(s, 0.4, 1.25, 12.5, filas, [1.7, 1.9, 8.9], tam=11, alto=0.4, izq=(0, 2), colores=col)
callout(s, 0.4, 6.55, 12.5, 0.45, "Rosa:", "es la variable que quiero predecir (y).", P_ROSA, tam=13)

# ═════════ 7 Otras variables ═════════
s = nueva("Variables que revisé y NO usé como predictoras", "Algunas variables las revisé pero no las usé. Unas son redundantes y otras causan fuga de información.")
filas = [["Variable", "Qué significa", "¿Por qué no la usé?"]] + [[v[0], v[1], v[2]] for v in OTRAS]
col = {}
for i, v in enumerate(OTRAS, start=1):
    if "Fuga" in v[2]:
        col[(i, 2)] = P_ROSA
    elif "Redundante" in v[2]:
        col[(i, 2)] = P_DURAZNO
    else:
        col[(i, 2)] = P_AZUL
tabla(s, 0.4, 1.25, 12.5, filas, [1.5, 6.5, 4.5], tam=11, alto=0.5, izq=(0, 1, 2), colores=col)
callout(s, 0.4, 6.4, 12.5, 0.55, "Colores:", "rosa = fuga de información · durazno = redundante · azul = solo la usé para filtrar, limpiar o comprobar.", P_AMARILLO, tam=13)

# ═════════ 8 Limpieza 1 ═════════
s = nueva("Limpieza (1): datos faltantes escritos como códigos",
          "En la ENOE casi no hay celdas vacías, pero lo que falta viene escrito como código, por ejemplo 99 igual a no especificado. Si no lo quito, el modelo piensa que alguien estudió 99 años.")
imagen(s, "f02_calidad", 0.4, 1.35, 6.6, 3.6)
viñetas(s, 7.2, 1.35, 5.7, 4.2, [
    ("Códigos → NaN: ", "99 en escolaridad, 9 en estado civil y 7 en sector."),
    ("Ingreso: ", "si no recibe ingresos, creé la columna sin_ingreso; si no se especificó, NaN."),
    ("Horas = 0: ", "ausencia temporal → NaN."),
    ("Duplicados: ", str(R["duplicados"]) + " filas repetidas."),
    ("Rellenar NaN: ", "mediana (calculada solo con entrenamiento) o la categoría “No especificado”."),
], tam=16)
callout(s, 0.4, 5.3, 12.5, 1.5, "¿Por qué la mediana?", "Porque casi no cambia con valores extremos. Si usara la media, unos pocos ingresos muy altos moverían el resultado. "
        "Lo más grande que encontré es el ingreso igual a 0 (muchas personas no reciben pago o no lo declararon).", P_DURAZNO)

# ═════════ 9 Limpieza 2 ═════════
s = nueva("Limpieza (2): valores atípicos", "Los atípicos son valores muy alejados del resto. Los detecté con la regla del IQR. No los borré: los limité al percentil 99.")
imagen(s, "f03_outliers", 0.4, 1.3, 12.5, 3.0)
at = R["atipicos"]
dato(s, 0.5, 4.45, 3.0, f(at["ingreso"]["porcentaje"], 1) + "%", "de los ingresos son atípicos", P_AZUL, h=1.25)
dato(s, 3.7, 4.45, 3.0, f(at["hrsocup"]["porcentaje"], 1) + "%", "de las horas son atípicas", P_DURAZNO, h=1.25)
viñetas(s, 6.9, 4.4, 6.0, 1.6, [
    ("Regla IQR: ", "es atípico lo que pasa de Q3 + 1.5 × (Q3 − Q1)."),
    ("Winsorizar: ", "al que pasa el tope le pongo el valor del tope (ingreso $" + miles(R["topes"]["ingreso"]) + ", horas " + miles(R["topes"]["horas"]) + ")."),
    ("Logaritmo: ", "hace menos “chueca” la distribución del ingreso."),
], tam=14, espacio=4)
callout(s, 0.5, 5.9, 12.4, 0.95, "Cómo leer el histograma de horas:", "casi todos trabajan entre 40 y 48 horas (la barra más alta) y a la derecha hay una cola con pocas personas que trabajan muchísimo; la línea punteada es el tope.", P_AMARILLO, tam=14)

# ═════════ 10 Preprocesamiento ═════════
s = nueva("Preprocesamiento: de categorías a números", "Los modelos solo entienden números. Por eso convertí las categorías con One-Hot Encoding, estandaricé y dividí en entrenamiento y prueba.")
caja(s, 0.5, 1.35, 6.1, 2.6, GRISC, NEGRO, 1)
texto(s, 0.65, 1.4, 5.8, 0.5, [[("One-Hot Encoding (pd.get_dummies)", True)]], tam=18)
tabla(s, 0.7, 1.95, 5.7, [["sexo", "→", "sexo_Mujer"], ["Hombre", "→", "0"], ["Mujer", "→", "1"]], [2.0, 0.9, 2.8], tam=15, alto=0.5,
      colores={(1, 2): P_AZUL, (2, 2): P_AZUL})
texto(s, 0.65, 3.45, 5.8, 0.45, ["Cada categoría pasa a una columna de 0 y 1."], tam=13)
caja(s, 6.8, 1.35, 6.0, 2.6, GRISC, NEGRO, 1)
texto(s, 6.95, 1.4, 5.7, 0.5, [[("Estandarizar (StandardScaler)", True)]], tam=18)
texto(s, 6.95, 1.95, 5.7, 2.0, ["Resta la media y divide entre la desviación estándar, para que todas las variables numéricas queden con media 0 y desviación 1.",
                                  "Solo la uso en la regresión logística, porque es sensible a la escala (los pesos en miles le ganarían a la edad). Los árboles no la necesitan."], tam=14)
tabla(s, 0.5, 4.2, 6.1, [["División de los datos", "Personas"], ["Entrenamiento (80%)", miles(R["n_train"])], ["Prueba (20%)", miles(R["n_test"])]],
      [3.6, 2.5], tam=15, alto=0.5, colores={(1, 1): P_MENTA, (2, 1): P_DURAZNO})
callout(s, 6.8, 4.2, 6.0, 1.5, "Sin fuga:", "la mediana, el percentil 99 y el escalador se calculan solo con entrenamiento y después se aplican a prueba. Así la prueba se comporta como datos nuevos.", P_ROSA, tam=14)
texto(s, 0.5, 5.95, 12.3, 0.9, ["stratify = y mantiene la misma proporción de informales (" + f(R["balance"]["Informal"], 1) + "%) en las dos partes."], tam=14)

# ═════════ 11 Verificación ═════════
s = nueva("¿La limpieza deformó los datos? No", "Comparé la media, la mediana y la correlación con la variable objetivo antes y después de limpiar. Casi no cambian, así que la limpieza no deformó la información.")
vf = R["verificacion"]
filas = [["Variable", "Media antes", "Media después", "Mediana antes", "Mediana después", "Corr. con y antes", "Corr. con y después"]]
for v in vf:
    filas.append([v["Variable"], f(v["Media antes"], 2), f(v["Media después"], 2), f(v["Mediana antes"], 2), f(v["Mediana después"], 2),
                  f(v["Corr. con y antes"], 3), f(v["Corr. con y después"], 3)])
col = {(i, j): P_MENTA for i in range(1, len(filas)) for j in (5, 6)}
tabla(s, 0.5, 1.3, 12.3, filas, [1.7, 1.7, 1.8, 1.8, 1.9, 1.7, 1.7], tam=13, alto=0.5, colores=col)
imagen(s, "f04_antes_despues", 0.5, 4.0, 12.3, 2.1)
callout(s, 0.5, 6.15, 12.3, 0.8, "Significa:", "las relaciones se conservan (por ejemplo, escolaridad: " + f(vf[1]["Corr. con y antes"]) + " antes y " + f(vf[1]["Corr. con y después"]) + " después). El ingreso es el que más cambia por los atípicos y los NaN.", P_MENTA, tam=14)

# ═════════ 12 Variables vs informalidad ═════════
s = nueva("Variables y su relación con la informalidad", "La informalidad baja mucho con la escolaridad, es mayor en localidades pequeñas y en agro y construcción. El sexo casi no marca diferencia.")
tr = R["tasas"]
imagen(s, "f05_tasas_grupo", 0.3, 1.3, 8.4, 4.7)
viñetas(s, 8.9, 1.35, 4.2, 4.6, [
    ("Escolaridad: ", f(tr["grupo_esc"]["0"], 0) + "% informal sin escuela → " + f(tr["grupo_esc"]["17+"], 0) + "% con 17 años o más."),
    ("Edad (forma de “U”): ", f(tr["grupo_edad"]["15-19"], 0) + "% a los 15–19, ≈45% a los 30–44 y " + f(tr["grupo_edad"]["65+"], 0) + "% a los 65+."),
    ("Localidad: ", f(tr["localidad"]["Menos de 2.5 mil"], 0) + "% en las pequeñas vs " + f(tr["localidad"]["Más de 100 mil"], 0) + "% en ciudades grandes."),
    ("Sexo: ", "casi igual (" + f(tr["sexo"]["Hombre"], 0) + "% y " + f(tr["sexo"]["Mujer"], 0) + "%)."),
], tam=15)
callout(s, 0.4, 6.1, 12.5, 0.85, "Cómo leerlo:", "la línea punteada es el promedio general. Si una barra sube mucho arriba de la línea, ese grupo es más informal que el promedio.", P_AZUL, tam=14)

# ═════════ 13 Estados y fuerza ═════════
s = nueva("¿Dónde y qué tan fuerte es la relación?", "El sur es más informal que el norte. Y entre todas las variables, la escolaridad es la que tiene la relación más fuerte con la informalidad.")
imagen(s, "f06_entidades", 0.4, 1.3, 5.2, 5.6)
imagen(s, "f07_relacion", 5.9, 1.3, 7.0, 3.3)
eh, eb = R["estados_altos"], R["estados_bajos"]
viñetas(s, 5.9, 4.7, 7.0, 1.3, [
    ("Más informales: ", ", ".join(k + " " + f(v, 0) + "%" for k, v in eh.items()) + "."),
    ("Menos informales: ", ", ".join(k + " " + f(v, 0) + "%" for k, v in eb.items()) + "."),
], tam=14, espacio=3)
callout(s, 5.9, 6.05, 7.0, 0.9, "Fuerza:", "V de Cramér (categóricas) o d de Cohen (numéricas): entre más grande, más fuerte la relación.", P_LILA, tam=13)

# ═════════ 14 Fuga ═════════
s = nueva("Fuga de información: una trampa que evité", "Si uso seguridad social como predictora, el modelo sale casi perfecto, pero es trampa, porque esa variable ya es parte de la definición de informalidad.")
fg = R["fuga"]
imagen(s, "f09_fuga", 0.4, 1.35, 7.4, 3.4)
viñetas(s, 8.1, 1.35, 4.9, 3.6, [
    ("El problema: ", "INEGI define la informalidad con seguridad social, posición en la ocupación y tamaño de la unidad."),
    ("La prueba: ", "sin ellas, AUC " + f(list(fg.values())[0], 2) + "; con las tres, " + f(fg["+ las tres juntas"], 2) + "."),
    ("Decisión: ", "las dejé fuera del modelo final."),
], tam=16)
callout(s, 0.4, 5.1, 12.5, 1.6, "Por qué importa:", "un AUC de 0.99 parece genial, pero no sirve: el modelo no está prediciendo, está leyendo la respuesta. "
        "Mi modelo sin esas variables sí puede predecir en casos donde no se conoce la seguridad social. "
        "También quité niv_ins y cs_p13_1 porque repiten la escolaridad (correlación " + f(R["corr_redundantes"]["niv_ins"], 2) + " y " + f(R["corr_redundantes"]["cs_p13_1"], 2) + ").", P_ROSA)

# ═════════ 15 Conceptos ═════════
s = nueva("Conceptos clave que uso (en palabras simples)", "Aquí explico los términos que voy a usar: validación cruzada, sobreajuste, GridSearchCV y los modelos.")
cuadros = [
    ("Validación cruzada (5 pliegues)", "Divido el entrenamiento en 5 partes; entreno con 4 y pruebo con 1, y repito 5 veces. Así sé qué tan bien funciona el modelo sin tocar la prueba.", P_AZUL),
    ("GridSearchCV", "Prueba todas las combinaciones de parámetros que le doy (por ejemplo, la profundidad del árbol) y se queda con la mejor.", P_DURAZNO),
    ("Sobreajuste", "Cuando el modelo se “aprende de memoria” los datos de entrenamiento y falla con datos nuevos. Lo detecto comparando entrenamiento contra prueba.", P_ROSA),
    ("Árbol y Random Forest", "El árbol hace preguntas de sí/no (“¿tiene más de 12 años de escuela?”). El Random Forest junta muchos árboles y promedia su respuesta.", P_MENTA),
]
for i, (t, d, c) in enumerate(cuadros):
    x, y = 0.5 + (i % 2) * 6.3, 1.4 + (i // 2) * 2.75
    caja(s, x, y, 6.0, 2.55, c, NEGRO, 1.25)
    texto(s, x + 0.15, y + 0.1, 5.7, 2.4, [[(t, True)], d], tam=16, espacio=8)

# ═════════ 16 Modelos ═════════
s = nueva("Modelos de aprendizaje automático", "Es un problema de clasificación. Usé tres modelos y un modelo base para comparar. Elegí el mejor con validación cruzada, no con la prueba.")
mp = R["mejores_parametros"]
tabla(s, 0.5, 1.35, 12.3, [
    ["Modelo", "¿Por qué lo usé?", "Mejores parámetros"],
    ["Regresión logística", "Modelo base, fácil de interpretar (odds ratio)", ", ".join(a + "=" + b for a, b in mp["Regresión logística"].items())],
    ["Árbol de decisión", "Reglas fáciles de entender", ", ".join(a + "=" + b for a, b in mp["Árbol de decisión"].items())],
    ["Random Forest", "Junta muchos árboles; sobreajusta menos", ", ".join(a + "=" + b for a, b in mp["Random Forest"].items())],
    ["Modelo base (Dummy)", "Siempre predice la clase más común", "—"],
], [2.8, 4.6, 4.9], tam=14, alto=0.55, izq=(0, 1), colores={(3, 0): P_MENTA, (3, 1): P_MENTA, (3, 2): P_MENTA})
viñetas(s, 0.5, 4.3, 7.6, 2.6, [
    ("Tipo de problema: ", "clasificación (informal o formal)."),
    ("Datos: ", "80% entrenamiento y 20% prueba."),
    ("Parámetros: ", "GridSearchCV con 5 pliegues, en una muestra de 30,000 filas para que no tarde."),
    ("Clases: ", f(R["balance"]["Informal"], 1) + "% informales y " + f(R["balance"]["Formal"], 1) + "% formales (casi balanceadas)."),
], tam=15)
callout(s, 8.3, 4.3, 4.5, 2.5, "Modelo base:", "si siempre digo “informal”, acierto " + f(M["Modelo base"]["accuracy"] * 100, 0) + "% sin aprender nada. Mis modelos deben ser mejores que eso.", P_AMARILLO, tam=15)

# ═════════ 17 Métricas ═════════
s = nueva("Cómo leer las métricas (con mi mejor modelo)", "Aquí explico cada métrica con un ejemplo de cada 100 personas, usando los números reales del Random Forest.")
mt = [("Accuracy", f(RS["accuracy"], 2), "Acierta " + f(RS["accuracy"] * 100, 0) + " de cada 100 personas.", P_AZUL),
      ("Precision", f(RS["precision"], 2), "De cada 100 que digo “informal”, " + f(RS["precision"] * 100, 0) + " sí lo son.", P_DURAZNO),
      ("Recall", f(RS["recall"], 2), "De cada 100 informales reales, encuentro " + f(RS["recall"] * 100, 0) + ".", P_MENTA),
      ("F1", f(RS["f1"], 2), "Mezcla de precision y recall en un solo número.", P_LILA),
      ("ROC-AUC", f(RS["auc_test"], 3), "Si tomo un informal y un formal al azar, " + f(RS["auc_test"] * 100, 1) + "% de las veces el modelo da más probabilidad al informal. 0.5 es azar; 1 es perfecto.", P_ROSA)]
for i, (n, v, d, c) in enumerate(mt):
    x, y = 0.5 + (i % 3) * 4.2, 1.4 + (i // 3) * 2.75
    w = 4.0
    caja(s, x, y, w, 2.55, c, NEGRO, 1.25)
    texto(s, x + 0.15, y + 0.05, w - 0.3, 0.5, [[(n, True)]], tam=18)
    texto(s, x + 0.15, y + 0.5, w - 0.3, 0.8, [[(v, True)]], tam=36)
    texto(s, x + 0.15, y + 1.35, w - 0.3, 1.2, [d], tam=14)
callout(s, 8.9, 4.15, 3.9, 2.7, "Meta:", "ROC-AUC ≥ 0.80 en prueba. Mi mejor modelo llegó a " + f(RS["auc_test"], 3) + ", así que se cumple.", P_AMARILLO, tam=15)

# ═════════ 18 Resultados ═════════
s = nueva("Resultados: el Random Forest fue el mejor", "El Random Forest tuvo el mejor AUC de validación cruzada y también el mejor en prueba. Los tres modelos superan al modelo base.")
nombres = ["Modelo base", "Regresión logística", "Árbol de decisión", "Random Forest"]
tabla(s, 0.5, 1.35, 7.4, [["Modelo", "Accuracy", "F1", "ROC-AUC"]] + [[n, f(M[n]["accuracy"], 3), f(M[n]["F1"], 3), f(M[n]["ROC-AUC"], 3)] for n in nombres],
      [3.0, 1.5, 1.4, 1.5], tam=15, alto=0.55, colores={(4, j): P_MENTA for j in range(4)})
imagen(s, "f12_roc", 8.1, 1.35, 4.8, 3.9)
dato(s, 0.5, 4.4, 3.6, f(RS["auc_test"], 3), "ROC-AUC en prueba (mejor modelo)", P_MENTA)
dato(s, 4.3, 4.4, 3.6, f(RS["f1"], 3), "F1 del Random Forest", P_AZUL)
callout(s, 0.5, 5.95, 12.4, 0.95, "Significa:", "la regresión logística rinde menos porque asume relaciones en línea recta; los árboles captan relaciones más complejas (como la forma de “U” de la edad).", P_AMARILLO, tam=14)

# ═════════ 19 Sobreajuste ═════════
s = nueva("¿Hay sobreajuste? Casi no", "Comparé el AUC de entrenamiento, validación y prueba. La diferencia del mejor modelo es de 0.016, menor al límite de 0.05.")
imagen(s, "f14_sobreajuste", 0.4, 1.3, 6.6, 3.6)
imagen(s, "f15_confusion", 7.3, 1.3, 3.6, 3.6)
cm = R["confusion"]
dato(s, 11.0, 1.4, 2.0, f(RS["diferencia"], 3), "diferencia train–test (límite 0.05)", P_MENTA, h=1.8)
viñetas(s, 0.5, 5.05, 7.0, 1.9, [
    ("Barras parecidas ", "entre entrenamiento, validación y prueba = el modelo generaliza."),
    ("Matriz de confusión: ", miles(cm[0][0]) + " formales y " + miles(cm[1][1]) + " informales bien clasificados."),
], tam=15)
callout(s, 7.7, 5.05, 5.2, 1.85, "Errores:", miles(cm[0][1]) + " formales que dije informales y " + miles(cm[1][0]) + " informales que se escaparon (recall " + f(RS["recall"], 2) + " vs precision " + f(RS["precision"], 2) + ").", P_ROSA, tam=14)

# ═════════ 20 Importancia ═════════
s = nueva("¿Qué variables pesan más?", "Las más importantes son escolaridad, horas trabajadas, ingreso y sector. El sexo casi no aporta.")
im = sorted(R["importancia"].items(), key=lambda x: -x[1])
imagen(s, "f18_importancia", 0.4, 1.35, 7.5, 4.6)
viñetas(s, 8.2, 1.4, 4.7, 3.2, [
    ("Top 4: ", ", ".join(k + " (" + f(v, 2) + ")" for k, v in im[:4]) + "."),
    ("Menos importantes: ", "sexo y estado civil (≈ 0.01)."),
], tam=16)
callout(s, 8.2, 3.6, 4.7, 2.35, "Interpretación:", "lo que más separa a una persona informal de una formal es cuánta escuela tiene, cuántas horas trabaja, cuánto gana y en qué sector trabaja.", P_AZUL, tam=15)
texto(s, 0.5, 6.1, 12.3, 0.8, ["La importancia viene del Random Forest: suma cuánto ayuda cada variable a separar formales de informales (todas suman 1)."], tam=14, color=GRIS)

# ═════════ 21 Hipótesis ═════════
s = nueva("Contraste de hipótesis", "H1 y H2 se respaldan. H3 no se sostiene como efecto independiente: el ingreso se explica por la escolaridad, las horas y el sector.")
col = {}
for i, h in enumerate(R["hipotesis"], start=1):
    col[(i, 4)] = P_MENTA if h["Veredicto"] == "RESPALDADA" else P_ROSA
tabla(s, 0.5, 1.35, 12.3, [["Hipótesis", "Prueba", "p-value", "Odds ratio", "Veredicto"]] +
      [[h["Hipótesis"], h["Prueba"], "< 0.001" if h["p-value"] < 0.001 else f(h["p-value"], 3), f(h["OR"], 2), h["Veredicto"].capitalize()] for h in R["hipotesis"]],
      [3.4, 2.4, 1.8, 2.0, 2.7], tam=16, alto=0.55, colores=col)
callout(s, 0.5, 3.95, 12.3, 1.0, "¿Qué es el odds ratio (OR)?", "Si es menor a 1, la variable baja la probabilidad de ser informal; si es mayor a 1, la sube. En las numéricas es por cada +1 desviación estándar.", P_LILA, tam=14)
viñetas(s, 0.5, 5.1, 12.3, 1.9, [
    ("H1: ", "OR " + f(HIP["H1"]["OR"], 2) + " → por cada desviación estándar más de escolaridad, los momios de ser informal bajan a menos de la mitad."),
    ("H2: ", f(R["tasa_rural"], 0) + "% de informalidad en localidades pequeñas vs " + f(R["tasa_urbana"], 0) + "% en ciudades grandes (OR " + f(HIP["H2"]["OR"], 2) + ")."),
    ("H3: ", "los informales ganan menos ($" + miles(R["ingreso_medio"]["informal"]) + " vs $" + miles(R["ingreso_medio"]["formal"]) +
     "), pero con escolaridad, horas y sector en el modelo, el OR del ingreso es " + f(HIP["H3"]["OR"], 2) + " (≈ 1): no es un efecto independiente."),
], tam=14, espacio=5)

# ═════════ 22 Eficiencia ═════════
s = nueva("Estructura y eficiencia del programa", "Lo más pesado es la búsqueda de parámetros con validación cruzada, sobre todo en el Random Forest. Medí cómo crece el tiempo con los datos.")
tm = R["tiempos"]
tabla(s, 0.5, 1.35, 6.3, [["Modelo", "Búsqueda (s)", "Entrenar (s)"]] +
      [[n, f(v["Búsqueda de parámetros (s)"], 1), f(v["Entrenamiento final (s)"], 1)] for n, v in tm.items()], [2.7, 1.8, 1.8], tam=14, alto=0.5,
      colores={(3, 1): P_ROSA})
viñetas(s, 0.5, 3.5, 6.3, 3.4, [
    ("Librerías: ", "pandas, numpy, matplotlib, seaborn, scipy y scikit-learn."),
    ("Etapas: ", "descargar → limpiar → dividir → entrenar → evaluar."),
    ("Reproducible: ", "random_state = 42; las predicciones salen idénticas al repetir."),
    ("Mejoras: ", "guardar el modelo con joblib, usar funciones y RandomizedSearchCV."),
], tam=14, espacio=5)
imagen(s, "f17_escalamiento", 7.0, 1.35, 5.9, 3.7)
callout(s, 7.0, 5.2, 5.9, 1.7, "Complejidad:", "regresión logística O(n·p), árbol O(n·p·log n), Random Forest O(T·n·p·log n). El tiempo medido crece más o menos proporcional a n.", P_AMARILLO, tam=13)

# ═════════ 23 Conclusiones ═════════
s = nueva("Conclusiones y limitaciones", "Lo que más aprendí fue a no confiar en un AUC demasiado bueno sin revisar primero si hay fuga de información.")
caja(s, 0.5, 1.35, 6.3, 5.5, P_MENTA, NEGRO, 1.25)
texto(s, 0.7, 1.45, 5.9, 0.5, [[("Conclusiones", True)]], tam=22)
viñetas(s, 0.7, 2.05, 5.9, 4.8, [
    "El Random Forest predice la informalidad con ROC-AUC de " + f(RS["auc_test"], 2) + " y casi sin sobreajuste.",
    "Escolaridad, horas, ingreso y sector son lo que más pesa.",
    "Se respaldan H1 y H2; H3 no se sostiene como efecto independiente.",
    "Hay que excluir las variables que definen la informalidad.",
], tam=16)
caja(s, 7.0, 1.35, 5.8, 5.5, P_DURAZNO, NEGRO, 1.25)
texto(s, 7.2, 1.45, 5.4, 0.5, [[("Limitaciones y trabajo futuro", True)]], tam=22)
viñetas(s, 7.2, 2.05, 5.4, 4.8, [
    "Solo un trimestre de la ENOE.",
    "No usé el factor de expansión en los modelos.",
    "Muestra relaciones, no causas.",
    "Futuro: varios trimestres, ponderar y probar otros modelos (gradient boosting).",
], tam=16)

# ═════════ 24 Cierre ═════════
s = prs.slides.add_slide(BLANK)
caja(s, 0, 0, 13.333, 7.5, NEGRO)
s.shapes.add_picture(FIG + "logo_cugdl_blanco.png", Inches(0.8), Inches(0.5), width=Inches(3.4))
texto(s, 0.8, 2.5, 11.7, 1.2, [[("¡Gracias! ¿Preguntas?", True)]], tam=44, color=BLANCO)
caja(s, 0.8, 3.8, 2.2, 0.09, P_DURAZNO)
caja(s, 3.1, 3.8, 1.2, 0.09, P_AZUL)
caja(s, 4.4, 3.8, 0.8, 0.09, P_MENTA)
texto(s, 0.8, 4.15, 11.7, 1.8, ["Melany Liliana Santillan Salazar", "Analítica Predictiva · Profesor Marco Antonio Cisneros Guevara",
                                 "Fuente de datos: INEGI, ENOE 2.º trimestre 2026"], tam=18, color=P_AZUL)

prs.save(ROOT + "Presentacion_Proyecto_ENOE.pptx")
print("presentacion lista:", len(prs.slides), "diapositivas")
