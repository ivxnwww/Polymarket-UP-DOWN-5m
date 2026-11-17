"""Arma la presentacion (PPTX) con las cifras reales del notebook."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diccionario import PRINCIPALES
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = "/home/user/Polymarket-UP-DOWN-5m/proyecto_enoe/"
R = json.load(open(ROOT + "resultados/resumen.json"))
FIG = ROOT + "figuras/"
M, RS = R["modelos"], R["resumen"]
HIP = {h["Hipótesis"][:2]: h for h in R["hipotesis"]}

AZUL = RGBColor(0x1E, 0x3A, 0x8A)
AZUL2 = RGBColor(0x25, 0x63, 0xEB)
NARANJA = RGBColor(0xF5, 0x9E, 0x0B)
GRIS = RGBColor(0x37, 0x41, 0x51)
CLARO = RGBColor(0xF3, 0xF4, 0xF6)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
VERDE = RGBColor(0x05, 0x96, 0x69)
ROJO = RGBColor(0xDC, 0x26, 0x26)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def f(x, d=3):
    return format(x, "." + str(d) + "f")


def miles(x):
    return format(int(round(x)), ",")


def caja(slide, x, y, w, h, color=None, linea=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    if color is None:
        s.fill.background()
    else:
        s.fill.solid(); s.fill.fore_color.rgb = color
    if linea is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = linea
    s.shadow.inherit = False
    return s


def texto(slide, x, y, w, h, partes, tam=18, color=GRIS, alinea=PP_ALIGN.LEFT, ancla=MSO_ANCHOR.TOP):
    """partes: lista de parrafos; cada parrafo es str o lista de (texto, negrita, color)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = ancla
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, par in enumerate(partes):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = alinea
        p.space_after = Pt(8)
        if isinstance(par, str):
            par = [(par, False, color)]
        for t, b, c in par:
            r = p.add_run(); r.text = t
            r.font.size = Pt(tam); r.font.bold = b; r.font.color.rgb = c or color
            r.font.name = "Calibri"
    return tb


def viñetas(slide, x, y, w, h, items, tam=18):
    partes = []
    for it in items:
        if isinstance(it, tuple):
            partes.append([("•  " + it[0], True, AZUL), (it[1], False, GRIS)])
        else:
            partes.append([("•  " + it, False, GRIS)])
    return texto(slide, x, y, w, h, partes, tam=tam)


def nueva(titulo, notas="", num=[0]):
    s = prs.slides.add_slide(BLANK)
    num[0] += 1
    caja(s, 0, 0, 13.333, 1.05, AZUL)
    s.shapes.add_picture(FIG + "logo_cugdl_blanco.png", Inches(11.35), Inches(0.2), width=Inches(1.75))
    texto(s, 0.5, 0.12, 10.6, 0.85, [titulo], tam=28, color=BLANCO, ancla=MSO_ANCHOR.MIDDLE)
    for r in s.shapes[-1].text_frame.paragraphs[0].runs:
        r.font.bold = True
    texto(s, 0.5, 7.05, 9, 0.35, ["Melany Liliana Santillan Salazar · Analítica Predictiva"], tam=11, color=RGBColor(0x6B, 0x72, 0x80))
    texto(s, 12.0, 7.05, 1.0, 0.35, [str(num[0] + 1)], tam=11, color=RGBColor(0x6B, 0x72, 0x80), alinea=PP_ALIGN.RIGHT)
    if notas:
        s.notes_slide.notes_text_frame.text = notas
    return s


def imagen(s, archivo, x, y, w=None, h=None):
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    return s.shapes.add_picture(FIG + archivo + ".png", Inches(x), Inches(y), **kw)


def dato(s, x, y, w, numero, etiqueta, color=AZUL2):
    caja(s, x, y, w, 1.45, CLARO)
    caja(s, x, y, 0.09, 1.45, color)
    texto(s, x + 0.25, y + 0.1, w - 0.3, 0.8, [numero], tam=32, color=color)
    s.shapes[-1].text_frame.paragraphs[0].runs[0].font.bold = True
    texto(s, x + 0.25, y + 0.85, w - 0.3, 0.6, [etiqueta], tam=13)


def tabla(s, x, y, w, filas, anchos, tam=14, alto=0.42, izq=(0,)):
    nfil, ncol = len(filas), len(filas[0])
    t = s.shapes.add_table(nfil, ncol, Inches(x), Inches(y), Inches(w), Inches(alto * nfil)).table
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
                r.font.bold = (i == 0)
                r.font.color.rgb = BLANCO if i == 0 else GRIS
            c.fill.solid()
            c.fill.fore_color.rgb = AZUL2 if i == 0 else (CLARO if i % 2 == 0 else BLANCO)
    return t


# 1 ── Portada
s = prs.slides.add_slide(BLANK)
caja(s, 0, 0, 13.333, 7.5, AZUL)
caja(s, 0.8, 3.55, 1.6, 0.07, NARANJA)
s.shapes.add_picture(FIG + "logo_cugdl_blanco.png", Inches(0.8), Inches(0.45), width=Inches(3.4))
texto(s, 0.8, 1.5, 11.5, 2.0, ["¿Quién trabaja en la informalidad?", "Predicción con datos de la ENOE (INEGI)"], tam=40, color=BLANCO)
for p in s.shapes[-1].text_frame.paragraphs:
    for r in p.runs:
        r.font.bold = True
texto(s, 0.8, 3.8, 11.5, 0.6, ["Proyecto integrador · Análisis de datos (tema libre)"], tam=22, color=RGBColor(0xBF, 0xDB, 0xFE))
texto(s, 0.8, 4.9, 11.5, 1.6, ["Alumna: Melany Liliana Santillan Salazar", "Materia: Analítica Predictiva · Profesor: Marco Antonio Cisneros Guevara",
                                "Centro Universitario de Guadalajara · Noviembre de 2026"], tam=18, color=BLANCO)
s.notes_slide.notes_text_frame.text = ("Hola, voy a presentar mi proyecto. Usé datos oficiales del INEGI para predecir si una persona que trabaja está en la informalidad.")

# 2 ── Problema
s = nueva("El problema: la informalidad laboral",
          "Más de la mitad de las personas que trabajan en México está en la informalidad. Quise saber qué características tienen y si se puede predecir.")
viñetas(s, 0.5, 1.4, 7.2, 5.4, [
    ("¿Qué es? ", "Trabajar sin seguridad social, sin prestaciones y sin contrato estable."),
    ("¿Por qué importa? ", "Quien está en la informalidad no tiene servicio médico por su trabajo ni ahorro para el retiro."),
    ("¿Por qué datos? ", "La ENOE tiene cientos de miles de personas; con tantos datos se necesitan modelos para ver qué pesa más."),
    ("Pregunta: ", "¿se puede predecir si una persona está en la informalidad con sus características?"),
], tam=19)
dato(s, 8.2, 1.5, 4.6, f(R["tasa_pond"] * 100, 1) + "%", "de las personas ocupadas está en la informalidad (con factor de expansión)")
dato(s, 8.2, 3.2, 4.6, miles(R["n_estudio"]), "personas ocupadas en mi población de estudio", NARANJA)
dato(s, 8.2, 4.9, 4.6, "2.º trim. 2026", "ENOE, INEGI (fuente oficial)", VERDE)

# 3 ── Objetivos e hipótesis
s = nueva("Objetivos e hipótesis", "Mi objetivo es clasificar a las personas ocupadas en informal o formal. Planteé tres hipótesis para comprobar con los datos.")
caja(s, 0.5, 1.4, 6.0, 5.4, CLARO)
texto(s, 0.7, 1.5, 5.6, 0.5, ["Objetivos"], tam=22, color=AZUL)
s.shapes[-1].text_frame.paragraphs[0].runs[0].font.bold = True
viñetas(s, 0.7, 2.1, 5.6, 4.6, [
    ("General: ", "predecir si una persona ocupada es informal (1) o formal (0)."),
    "Limpiar los datos y revisar que no haya fuga de información.",
    "Comparar 3 modelos con validación cruzada.",
    "Lograr ROC-AUC ≥ 0.80 en prueba.",
    "Explicar qué variables pesan más.",
], tam=17)
caja(s, 6.8, 1.4, 6.0, 5.4, CLARO)
texto(s, 7.0, 1.5, 5.6, 0.5, ["Hipótesis"], tam=22, color=AZUL)
s.shapes[-1].text_frame.paragraphs[0].runs[0].font.bold = True
viñetas(s, 7.0, 2.1, 5.6, 4.6, [
    ("H1: ", "a más escolaridad, menos informalidad."),
    ("H2: ", "vivir en localidad de menos de 2,500 habitantes aumenta la informalidad."),
    ("H3: ", "a mayor ingreso, menos informalidad."),
    ("Se respalda ", "si la prueba da p < 0.05 y el odds ratio va en la dirección esperada."),
], tam=17)

# 4 ── Datos
s = nueva("Procedencia de los datos", "Descargué la base del sitio de datos abiertos del INEGI. No usé Kaggle, ni encuestas propias, ni scraping.")
viñetas(s, 0.5, 1.4, 6.3, 5.5, [
    ("Fuente: ", "INEGI, Encuesta Nacional de Ocupación y Empleo (ENOE), 2.º trimestre 2026."),
    ("Cómo la obtuve: ", "descarga del repositorio oficial de datos abiertos (zip de 41 MB), tabla SDEM."),
    ("Tamaño: ", miles(R["n_registros"]) + " registros y " + str(R["n_variables"]) + " variables."),
    ("Confiable: ", "diseño de muestra oficial, diccionario de datos y catálogos públicos."),
    ("Comprobación: ", "con factor de expansión la informalidad da " + f(R["tasa_pond"] * 100, 1) + "%, parecida a la de INEGI."),
], tam=17)
imagen(s, "f01_embudo", 7.0, 1.9, w=5.9)
texto(s, 7.0, 4.5, 5.9, 1.2, ["Me quedé con las personas ocupadas de 15 años o más, clasificadas como formales o informales."], tam=15)

# 5 ── Limpieza 1
s = nueva("Limpieza (1): datos faltantes escritos como códigos",
          "En la ENOE casi no hay celdas vacías, pero los datos que faltan vienen como códigos, por ejemplo 99 igual a no especificado. Los cambié por NaN.")
imagen(s, "f02_calidad", 0.4, 1.4, w=7.0)
viñetas(s, 7.6, 1.4, 5.3, 5.4, [
    ("Códigos → NaN: ", "99 en escolaridad, 9 en estado civil, 7 en sector e ingreso."),
    ("Ingreso: ", "si no recibe ingresos creé la columna sin_ingreso; si no se especificó, NaN."),
    ("Horas = 0: ", "ausencia temporal → NaN."),
    ("Duplicados: ", str(R["duplicados"]) + " filas repetidas."),
    ("Rellenar NaN: ", "mediana (solo con entrenamiento) o categoría “No especificado”."),
], tam=16)

# 6 ── Limpieza 2
s = nueva("Limpieza (2): valores atípicos y preprocesamiento",
          "Los atípicos los detecté con la regla del IQR y los limité al percentil 99. No eliminé filas. Las categorías las convertí con get_dummies.")
imagen(s, "f03_outliers", 0.4, 1.3, w=8.0)
viñetas(s, 8.6, 1.3, 4.4, 3.2, [
    ("Atípicos (IQR): ", "ingreso " + f(R["atipicos"]["ingreso"]["porcentaje"], 1) + "%, horas " + f(R["atipicos"]["hrsocup"]["porcentaje"], 1) + "%."),
    ("Tratamiento: ", "tope en el percentil 99 + logaritmo."),
], tam=16)
caja(s, 0.5, 4.3, 12.4, 2.6, CLARO)
viñetas(s, 0.7, 4.4, 12.0, 2.5, [
    ("Cualitativas → números: ", "One-Hot Encoding (pd.get_dummies, drop_first=True)."),
    ("División: ", "80% entrenamiento (" + miles(R["n_train"]) + ") y 20% prueba (" + miles(R["n_test"]) + "), con stratify."),
    ("Estandarización (StandardScaler): ", "solo en la regresión logística, porque es sensible a la escala."),
    ("Sin fuga: ", "medianas, percentiles y escalador se calculan solo con entrenamiento."),
], tam=16)

# 6b ── Diccionario de variables
s = nueva("Diccionario de variables", "Aquí explico cada variable: cómo se llama en mi código, cómo se llama en la ENOE y qué significa.")
filas = [["En mi código", "En la ENOE", "Qué significa"]] + [[v[0], v[1], v[2]] for v in PRINCIPALES]
tabla(s, 0.4, 1.25, 12.5, filas, [1.7, 1.9, 8.9], tam=12, alto=0.45, izq=(0, 2))

# 7 ── Variables
s = nueva("Variables y su relación con la informalidad",
          "La informalidad baja mucho con la escolaridad, es mayor en localidades pequeñas y en agro y construcción. El sexo casi no marca diferencia.")
imagen(s, "f05_tasas_grupo", 0.3, 1.25, w=8.6)
tr = R["tasas"]
viñetas(s, 9.1, 1.4, 4.0, 5.5, [
    ("Objetivo (y): ", "informal = 1, formal = 0."),
    ("Predictoras: ", "edad, escolaridad, horas, ingreso, sin_ingreso, sexo, estado civil, localidad, sector y estado."),
    ("Escolaridad: ", f(tr["grupo_esc"]["0"], 0) + "% → " + f(tr["grupo_esc"]["17+"], 0) + "% informal."),
    ("Localidad pequeña: ", f(tr["localidad"]["Menos de 2.5 mil"], 0) + "% vs " + f(tr["localidad"]["Más de 100 mil"], 0) + "% en ciudades grandes."),
], tam=15)

# 8 ── Fuga
s = nueva("Fuga de información: una trampa que evité",
          "Si uso seguridad social como predictora, el modelo sale casi perfecto, pero es trampa porque esa variable ya define la informalidad.")
imagen(s, "f09_fuga", 0.4, 1.4, w=7.6)
fg = R["fuga"]
viñetas(s, 8.3, 1.4, 4.7, 5.4, [
    ("El problema: ", "INEGI define informalidad con seguridad social, posición en la ocupación y tamaño de la unidad."),
    ("La prueba: ", "mi modelo da AUC " + f(list(fg.values())[0], 2) + "; con las tres variables sube a " + f(fg["+ las tres juntas"], 2) + "."),
    ("Decisión: ", "las excluí del modelo final."),
    ("Redundantes: ", "niv_ins y cs_p13_1 repiten la escolaridad (correlación " + f(R["corr_redundantes"]["niv_ins"], 2) + " y " + f(R["corr_redundantes"]["cs_p13_1"], 2) + ")."),
], tam=16)

# 9 ── Modelos
s = nueva("Modelos de aprendizaje automático",
          "Es un problema de clasificación. Usé tres modelos y un modelo base para comparar. Elegí el mejor con validación cruzada, no con la prueba.")
tabla(s, 0.5, 1.4, 12.3, [
    ["Modelo", "¿Por qué lo usé?", "Mejores parámetros"],
    ["Regresión logística", "Modelo base, fácil de interpretar", ", ".join(a + "=" + b for a, b in R["mejores_parametros"]["Regresión logística"].items())],
    ["Árbol de decisión", "Reglas fáciles de entender", ", ".join(a + "=" + b for a, b in R["mejores_parametros"]["Árbol de decisión"].items())],
    ["Random Forest", "Junta muchos árboles; sobreajusta menos", ", ".join(a + "=" + b for a, b in R["mejores_parametros"]["Random Forest"].items())],
    ["Modelo base (Dummy)", "Siempre predice la clase más común", "—"],
], [2.8, 4.6, 4.9], tam=14, alto=0.55)
viñetas(s, 0.5, 4.4, 12.3, 2.6, [
    ("Tipo de problema: ", "clasificación (informal o formal)."),
    ("Búsqueda de parámetros: ", "GridSearchCV con validación cruzada de 5 pliegues (muestra de 30,000 filas)."),
    ("Métricas: ", "accuracy, precision, recall, F1 y ROC-AUC."),
    ("Clases casi balanceadas: ", f(R["balance"]["Informal"], 1) + "% informales y " + f(R["balance"]["Formal"], 1) + "% formales."),
], tam=16)

# 10 ── Resultados
s = nueva("Resultados: el Random Forest fue el mejor", "El Random Forest tuvo el mejor AUC de validación cruzada y también el mejor en prueba.")
nombres = ["Modelo base", "Regresión logística", "Árbol de decisión", "Random Forest"]
tabla(s, 0.5, 1.4, 7.4, [["Modelo", "Accuracy", "F1", "ROC-AUC"]] + [[n, f(M[n]["accuracy"], 3), f(M[n]["F1"], 3), f(M[n]["ROC-AUC"], 3)] for n in nombres],
      [3.0, 1.5, 1.4, 1.5], tam=15, alto=0.55)
dato(s, 0.5, 4.5, 3.5, f(RS["auc_test"], 3), "ROC-AUC en prueba (meta ≥ 0.80)", VERDE)
dato(s, 4.3, 4.5, 3.6, f(RS["f1"], 3), "F1 del Random Forest")
imagen(s, "f12_roc", 8.2, 1.4, w=4.9)
texto(s, 8.2, 5.5, 4.9, 1.3, ["Los tres modelos superan al modelo base (AUC 0.5), así que sí aprenden."], tam=14)

# 11 ── Sobreajuste
s = nueva("¿Hay sobreajuste? Casi no",
          "Comparé el AUC de entrenamiento, validación y prueba. La diferencia del mejor modelo es de apenas 0.016, menor al límite de 0.05.")
imagen(s, "f14_sobreajuste", 0.4, 1.4, w=6.6)
imagen(s, "f15_confusion", 7.3, 1.4, w=3.7)
cm = R["confusion"]
viñetas(s, 7.3, 5.1, 5.7, 1.9, [
    ("Diferencia train–test: ", f(RS["diferencia"], 3) + " (límite 0.05)."),
    ("Errores: ", miles(cm[0][1]) + " formales dichos informales y " + miles(cm[1][0]) + " informales que se escaparon."),
], tam=14)
texto(s, 0.5, 5.0, 6.5, 1.8, ["La regresión logística no sobreajusta pero rinde menos: asume relaciones en línea recta y aquí hay relaciones más complicadas (por ejemplo, la edad tiene forma de “U”)."], tam=14)

# 12 ── Importancia
s = nueva("¿Qué variables pesan más?", "Las más importantes son escolaridad, horas trabajadas, ingreso y sector. El sexo casi no aporta.")
imagen(s, "f18_importancia", 0.4, 1.4, w=7.4)
im = sorted(R["importancia"].items(), key=lambda x: -x[1])
viñetas(s, 8.1, 1.5, 4.9, 5.3, [
    ("Top 4: ", ", ".join(k + " (" + f(v, 2) + ")" for k, v in im[:4]) + "."),
    ("Menos importantes: ", "sexo y estado civil (≈ 0.01)."),
    ("Interpretación: ", "lo que más separa a un informal de un formal es cuánta escuela tiene, cuánto trabaja, cuánto gana y en qué sector."),
], tam=17)

# 13 ── Hipótesis
s = nueva("Contraste de hipótesis", "H1 y H2 se respaldan. H3 no se sostiene como efecto independiente: el ingreso se explica por escolaridad, horas y sector.")
def vh(h): return h["Veredicto"].capitalize()
tabla(s, 0.5, 1.4, 12.3, [["Hipótesis", "Prueba", "p-value", "Odds ratio", "Veredicto"]] +
      [[h["Hipótesis"], h["Prueba"], "< 0.001" if h["p-value"] < 0.001 else f(h["p-value"], 3), f(h["OR"], 2), vh(h)] for h in R["hipotesis"]],
      [3.4, 2.4, 1.8, 2.0, 2.7], tam=16, alto=0.6)
viñetas(s, 0.5, 4.0, 12.3, 3.0, [
    ("H1: ", "por cada desviación estándar más de escolaridad, los momios de ser informal bajan a " + f(HIP["H1"]["OR"], 2) + " (menos de la mitad)."),
    ("H2: ", f(R["tasa_rural"], 0) + "% de informalidad en localidades pequeñas vs " + f(R["tasa_urbana"], 0) + "% en ciudades grandes."),
    ("H3: ", "los informales ganan menos ($" + miles(R["ingreso_medio"]["informal"]) + " vs $" + miles(R["ingreso_medio"]["formal"]) +
     "), pero con escolaridad, horas y sector en el modelo el odds ratio del ingreso es ≈ 1: no es un efecto independiente."),
], tam=16)

# 14 ── Eficiencia
s = nueva("Estructura y eficiencia del programa",
          "Lo más pesado es la búsqueda de parámetros con validación cruzada, sobre todo en el Random Forest. Medí cómo crece el tiempo con los datos.")
tm = R["tiempos"]
tabla(s, 0.5, 1.4, 6.2, [["Modelo", "Búsqueda (s)", "Entrenar (s)"]] +
      [[n, f(v["Búsqueda de parámetros (s)"], 1), f(v["Entrenamiento final (s)"], 1)] for n, v in tm.items()], [2.7, 1.8, 1.7], tam=14, alto=0.5)
viñetas(s, 0.5, 3.6, 6.2, 3.4, [
    ("Librerías: ", "pandas, numpy, matplotlib, seaborn, scipy y scikit-learn."),
    ("Etapas: ", "descargar → limpiar → dividir → entrenar → evaluar."),
    ("Reproducible: ", "random_state = 42; las predicciones salen idénticas al repetir."),
    ("Mejoras: ", "guardar el modelo con joblib, usar funciones y RandomizedSearchCV."),
], tam=15)
imagen(s, "f17_escalamiento", 7.0, 1.4, w=6.0)
texto(s, 7.0, 5.3, 6.0, 1.5, ["Complejidad: regresión logística O(n·p), árbol O(n·p·log n), Random Forest O(T·n·p·log n). El tiempo medido crece más o menos proporcional a n."], tam=13)

# 15 ── Conclusiones
s = nueva("Conclusiones y limitaciones", "Lo que más aprendí fue a no confiar en un AUC demasiado bueno sin revisar primero si hay fuga de información.")
caja(s, 0.5, 1.4, 6.3, 5.5, CLARO)
texto(s, 0.7, 1.5, 5.9, 0.5, ["Conclusiones"], tam=22, color=AZUL)
s.shapes[-1].text_frame.paragraphs[0].runs[0].font.bold = True
viñetas(s, 0.7, 2.1, 5.9, 4.8, [
    "El Random Forest predice la informalidad con ROC-AUC de " + f(RS["auc_test"], 2) + " y casi sin sobreajuste.",
    "Escolaridad, horas, ingreso y sector son lo que más pesa.",
    "Se respaldan H1 y H2; H3 no se sostiene como efecto independiente.",
    "Hay que excluir las variables que definen la informalidad.",
], tam=16)
caja(s, 7.0, 1.4, 5.8, 5.5, CLARO)
texto(s, 7.2, 1.5, 5.4, 0.5, ["Limitaciones y trabajo futuro"], tam=22, color=AZUL)
s.shapes[-1].text_frame.paragraphs[0].runs[0].font.bold = True
viñetas(s, 7.2, 2.1, 5.4, 4.8, [
    "Solo un trimestre de la ENOE.",
    "No usé el factor de expansión en los modelos.",
    "Muestra relaciones, no causas.",
    "Futuro: varios trimestres, ponderar y probar gradient boosting.",
], tam=16)

# 16 ── Cierre
s = prs.slides.add_slide(BLANK)
caja(s, 0, 0, 13.333, 7.5, AZUL)
texto(s, 0.8, 2.5, 11.7, 1.2, ["¡Gracias! ¿Preguntas?"], tam=44, color=BLANCO)
s.shapes[-1].text_frame.paragraphs[0].runs[0].font.bold = True
caja(s, 0.8, 3.75, 1.6, 0.07, NARANJA)
s.shapes.add_picture(FIG + "logo_cugdl_blanco.png", Inches(0.8), Inches(0.45), width=Inches(3.4))
texto(s, 0.8, 4.1, 11.7, 1.5, ["Melany Liliana Santillan Salazar", "Analítica Predictiva · Profesor Marco Antonio Cisneros Guevara",
                                "Fuente: INEGI, ENOE 2.º trimestre 2026"], tam=18, color=RGBColor(0xBF, 0xDB, 0xFE))

prs.save(ROOT + "Presentacion_Proyecto_ENOE.pptx")
print("presentacion lista:", len(prs.slides), "diapositivas")
