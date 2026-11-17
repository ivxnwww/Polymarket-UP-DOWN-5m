"""Construye el notebook de Colab del proyecto (ENOE - informalidad laboral)."""
import nbformat as nbf

C = []
def md(s):   C.append(nbf.v4.new_markdown_cell(s.strip("\n")))
def code(s): C.append(nbf.v4.new_code_cell(s.strip("\n")))

# ───────────────────────────── Portada ─────────────────────────────
md(r"""
# ¿Quién trabaja en la informalidad? Modelo predictivo con la ENOE (INEGI)
**Proyecto integrador · Análisis de datos (tema libre)** · Centro Universitario de Guadalajara

**Fuente oficial:** INEGI, *Encuesta Nacional de Ocupación y Empleo (ENOE)*, población de 15 años y más, **2.º trimestre de 2026** (tabla sociodemográfica `SDEM`).

**Cómo usar este notebook en Google Colab:** *Entorno de ejecución → Ejecutar todo*. La primera celda de datos descarga la base directamente del sitio de INEGI (≈ 41 MB); no hay que subir ningún archivo. Todo es reproducible (semilla 42). Tarda unos minutos, sobre todo la búsqueda de hiperparámetros (sección 4).

**Estructura (igual que el documento):**
0. Planteamiento, objetivos e hipótesis · 1. Procedencia de los datos · 2. Limpieza y preprocesamiento · 3. Variables · 4. Modelos · 5. Eficiencia del programa · 6. Resultados y conclusiones
""")

# ───────────────────────────── Configuración ─────────────────────────────
md(r"""
## Configuración general
Importamos las bibliotecas (cada una con su función) y fijamos la semilla para que los resultados se puedan reproducir.

| Biblioteca | Para qué la usamos |
|---|---|
| `numpy`, `pandas` | matrices y tablas de datos |
| `matplotlib`, `seaborn` | gráficas |
| `scipy.stats` | pruebas estadísticas (χ², Mann-Whitney, KS) |
| `statsmodels` | regresión logística con p-values e intervalos (razones de momios) |
| `scikit-learn` | preprocesamiento, modelos, validación cruzada y métricas |
""")
code(r"""
import os, time, json, warnings, urllib.request, zipfile
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, seaborn as sns
from scipy import stats
from IPython.display import display, Markdown

from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import (train_test_split, StratifiedKFold, RandomizedSearchCV,
                                     GridSearchCV, validation_curve)
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score, roc_curve,
                             precision_recall_curve, confusion_matrix, ConfusionMatrixDisplay)
from sklearn.inspection import permutation_importance, PartialDependenceDisplay
from threadpoolctl import threadpool_limits
import statsmodels.api as sm

warnings.filterwarnings("ignore")
SEED = 42
np.random.seed(SEED)
os.makedirs("figuras", exist_ok=True); os.makedirs("resultados", exist_ok=True)

AZUL, NARANJA, GRIS, VERDE, ROJO = "#2563EB", "#F59E0B", "#6B7280", "#10B981", "#DC2626"
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 170, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25,
                     "font.size": 10, "axes.titleweight": "bold"})
R = {}   # diccionario con todos los resultados (lo usa el reporte y la presentación)

def guardar(nombre):
    plt.tight_layout(); plt.savefig(f"figuras/{nombre}.png", bbox_inches="tight"); plt.show()
""")

# ───────────────────────────── 0 ─────────────────────────────
md(r"""
## 0. Planteamiento, objetivos e hipótesis

**Problema.** En México más de la mitad de las personas ocupadas trabaja en la **informalidad**: sin seguridad social, sin prestaciones y con menor estabilidad. Saber *qué características se asocian* a ese estatus (y con qué precisión se puede *predecir*) sirve para focalizar programas de formalización, inspección y seguridad social.

**Objetivo general.** Construir y evaluar modelos de clasificación que predigan si una persona ocupada está en empleo **informal** (`1`) o **formal** (`0`) usando solo características sociodemográficas y laborales *no definitorias* de la informalidad.

**Objetivos específicos (medibles).**
1. Documentar la procedencia de la base y depurarla (nulos, códigos "no especificado", duplicados, atípicos).
2. Identificar y justificar las variables predictoras y detectar variables con **fuga de información**.
3. Comparar 4 modelos (regresión logística, árbol, bosque aleatorio, gradient boosting) frente a una línea base, con validación cruzada de 5 pliegues.
4. Alcanzar **ROC-AUC ≥ 0.80** en prueba, sin sobreajuste relevante (diferencia entrenamiento–prueba < 0.05).
5. Interpretar qué variables pesan más y contrastar las hipótesis.

**Hipótesis.**
- **H1.** A mayor escolaridad, menor probabilidad de informalidad.
- **H2.** Vivir en una localidad pequeña (< 2,500 habitantes) aumenta la probabilidad de informalidad respecto a una ciudad grande.
- **H3.** A mayor ingreso por trabajo, menor probabilidad de informalidad.

*Contraste:* razones de momios (OR) de una regresión logística con intervalos de confianza al 95 %, pruebas χ² / Mann-Whitney y la importancia de variables del mejor modelo. *Se respalda* una hipótesis si el OR tiene el sentido esperado, su IC 95 % no incluye 1 (p < 0.05) y la variable pesa en el modelo predictivo; *se rechaza* si el IC incluye 1 o el sentido es contrario.
""")

# ───────────────────────────── 1 ─────────────────────────────
md(r"""
## 1. Procedencia y adquisición de la base de datos

- **Fuente original:** INEGI, ENOE, *Conjunto de datos abiertos* (https://www.inegi.org.mx/programas/enoe/15ymas/). Es una **encuesta probabilística nacional** levantada por INEGI; nosotros solo **consultamos el repositorio oficial** (no hubo trabajo de campo ni *scraping*).
- **Por qué esta fuente:** es la fuente oficial de las cifras de empleo e informalidad de México, trae diccionario de datos y catálogos, es pública y tiene un tamaño suficiente para aprendizaje automático.
- **Tabla usada:** `SDEM` (características sociodemográficas y variables laborales ya construidas por INEGI, como `emp_ppal`, que marca empleo informal/formal).

La siguiente celda descarga el archivo directamente del sitio de INEGI y extrae la tabla `SDEM`.
""")
code(r"""
URL = "https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/datosabiertos/2026/conjunto_de_datos_enoe_2026_2t_csv.zip"
ZIP = "datos/enoe_2026_2t.zip"
os.makedirs("datos", exist_ok=True)
if not os.path.exists(ZIP):
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(ZIP, "wb") as f:
        while True:                                   # descarga por bloques (evita cargar todo en memoria)
            bloque = r.read(1 << 20)
            if not bloque: break
            f.write(bloque)
with zipfile.ZipFile(ZIP) as z:                       # solo extraemos la tabla sociodemográfica
    z.extractall("datos/enoe", members=[m for m in z.namelist() if "sdem" in m])

BASE = "datos/enoe/conjunto_de_datos_sdem_enoe_2026_2t"
raw = pd.read_csv(f"{BASE}/conjunto_de_datos/conjunto_de_datos_sdem_enoe_2026_2t.csv",
                  encoding="latin1", low_memory=False)
dicc = pd.read_csv(f"{BASE}/diccionario_de_datos/diccionario_datos_sdem_enoe_2026_2t.csv", encoding="latin1")
ENT = pd.read_csv(f"{BASE}/catalogos/cve_ent.csv", encoding="latin1", dtype=str)
ENT = {int(a): b for a, b in zip(ENT["CVE_ENT"], ENT["DESCRIP"])}

# Pasamos a número las columnas que usaremos (los blancos " " pasan a NaN)
USAR = ["eda","sex","anios_esc","niv_ins","cs_p13_1","e_con","t_loc_tri","cve_ent","ur","rama","hrsocup","ingocup",
        "ing7c","clase2","emp_ppal","fac_tri","pos_ocu","emple7c","seg_soc","tue_ppal","ambito1","sec_ins",
        "imssissste","remune2c","tcco"]
for c in USAR: raw[c] = pd.to_numeric(raw[c], errors="coerce")

R["n_registros"], R["n_variables"] = int(raw.shape[0]), int(raw.shape[1])
print(f"Registros: {raw.shape[0]:,} | Variables: {raw.shape[1]} | Variables documentadas en el diccionario: {len(dicc)}")
raw.iloc[:5, :12]
""")
md(r"""
**Criterios de confiabilidad, pertinencia y suficiencia.** (i) Fuente oficial con diseño muestral probabilístico y diccionario/catálogos públicos; (ii) la variable objetivo (`emp_ppal`) es la medición oficial de informalidad; (iii) validamos que, ponderando con el factor de expansión, la tasa de informalidad se parezca a la cifra publicada por INEGI; (iv) hay cientos de miles de registros, suficientes para entrenar y probar.

Definimos la **población de estudio**: personas ocupadas (`clase2 == 1`) de 15 años o más con clasificación formal/informal (`emp_ppal` ∈ {1, 2}).
""")
code(r"""
n0 = len(raw)
n1 = int((raw.eda >= 15).sum())
n2 = int(((raw.eda >= 15) & (raw.clase2 == 1)).sum())
d = raw[(raw.eda.between(15, 98)) & (raw.clase2 == 1) & (raw.emp_ppal.isin([1, 2]))].copy()
n3 = len(d)
d["y"] = (d.emp_ppal == 1).astype(int)          # 1 = informal, 0 = formal
R["embudo"] = {"Registros totales ENOE": n0, "Personas de 15 años y más": n1, "Población ocupada": n2, "Ocupados clasificados (estudio)": n3}

tasa_pond = float((d.fac_tri * d.y).sum() / d.fac_tri.sum())     # tasa con factor de expansión
tasa_muestra = float(d.y.mean())                                  # tasa sin ponderar (la que ve el modelo)
R.update(n_estudio=n3, tasa_informal_pond=tasa_pond, tasa_informal_muestra=tasa_muestra)
print(f"Población de estudio: {n3:,} personas ocupadas")
print(f"Tasa de informalidad ponderada (factor de expansión): {tasa_pond:.1%}   <- comparable con INEGI")
print(f"Tasa de informalidad en la muestra (sin ponderar):    {tasa_muestra:.1%}")

fig, ax = plt.subplots(figsize=(8, 3.2))
etq, val = list(R["embudo"].keys()), list(R["embudo"].values())
ax.barh(etq[::-1], val[::-1], color=[AZUL, "#60A5FA", "#93C5FD", "#BFDBFE"][::-1])
for i, v in enumerate(val[::-1]): ax.text(v, i, f" {v:,}", va="center")
ax.set_xlim(0, n0 * 1.18); ax.set_title("De la base completa a la población de estudio"); ax.grid(False)
guardar("f01_embudo")
""")

# ───────────────────────────── 2 ─────────────────────────────
md(r"""
## 2. Limpieza y preprocesamiento

### 2.1 Auditoría de calidad (base original)
La ENOE casi no trae `NaN`: los datos faltantes están **codificados** (por ejemplo, 99 = "no especificado", 9 = "no sabe", 7 = "no especificado"). Si no se detectan, el modelo los trataría como números reales. Revisamos cada variable contra su catálogo.
""")
code(r"""
aud = pd.DataFrame({
  "Variable": ["anios_esc","e_con","niv_ins","rama","ing7c","hrsocup","ingocup","sex","eda"],
  "Problema detectado": ['99 = "no especificado"','9 = "no sabe"','5 = "no especificado"','7 = "no especificado"',
                         '7 = "no especificado" (ingreso)','0 horas (ausencia temporal)','0 = sin ingreso o no declarado',
                         'espacio en blanco','12–14 años (fuera de 15+)'],
  "Registros": [int((d.anios_esc==99).sum()), int((d.e_con==9).sum()), int((d.niv_ins==5).sum()), int((d.rama==7).sum()),
                int((d.ing7c==7).sum()), int((d.hrsocup==0).sum()), int((d.ingocup==0).sum()), int(d.sex.isna().sum()),
                int((raw[(raw.clase2==1)&raw.emp_ppal.isin([1,2])].eda<15).sum())]})
aud["% de la población"] = (100 * aud["Registros"] / len(d)).round(2)
R["auditoria"] = aud.to_dict("records")
display(aud)

fig, ax = plt.subplots(figsize=(8, 3.6))
a = aud.sort_values("% de la población")
ax.barh(a["Variable"], a["% de la población"], color=NARANJA)
for i, v in enumerate(a["% de la población"]): ax.text(v, i, f" {v:.1f}%", va="center")
ax.set_title("Valores problemáticos por variable (% de ocupados)"); ax.grid(False)
guardar("f02_calidad")

# Duplicados: (a) filas idénticas y (b) misma persona (llave de identificación) repetida
llave = ["cve_ent","upm","con","v_sel","n_hog","h_mud","n_ent","per","n_ren","mes_cal"]
llave = [c for c in llave if c in raw.columns]
dup_filas = int(d.duplicated().sum())
dup_llave = int(raw.loc[d.index].duplicated(llave).sum())
R["dup_filas"], R["dup_llave"] = dup_filas, dup_llave
print(f"Filas totalmente duplicadas: {dup_filas} | Personas repetidas por llave de identificación: {dup_llave}")
print("Cruce ingreso declarado: ing7c vs ingocup==0")
print(pd.crosstab(d.ing7c, d.ingocup.eq(0), rownames=["ing7c"], colnames=["ingocup==0"]))
""")
md(r"""
### 2.2 Tratamiento de nulos, códigos especiales y duplicados
Reglas que aplicamos (todas filas→filas, sin mirar la variable objetivo, por lo que **no hay fuga**):
- Códigos "no especificado / no sabe" → `NaN` explícito (`anios_esc`=99, `e_con`=9, `rama`=7).
- Ingreso: `ing7c = 7` (no especificado) → `NaN`; `ing7c = 6` (no recibe ingresos) es información real → se conserva el 0 y se crea la bandera `sin_ingreso`.
- Horas: `hrsocup = 0` (ausencia temporal) → `NaN`.
- Los `NaN` **se imputan dentro del `Pipeline`, ajustando solo con entrenamiento** (mediana en numéricas; categoría "No especificado" en categóricas), para no filtrar información de la prueba.
- Duplicados: si existieran, se eliminarían; aquí se reporta el conteo.
""")
code(r"""
d = d.drop_duplicates()
d["anios_esc"]   = d.anios_esc.where(d.anios_esc < 99)
d["hrsocup"]     = d.hrsocup.where(d.hrsocup > 0)
d["sin_ingreso"] = (d.ing7c == 6).astype(int)
d["ingocup_c"]   = d.ingocup.where(d.ing7c != 7)

# Etiquetas legibles (de los catálogos de INEGI) -> también es la transformación cualitativa
d["sex"]    = d.sex.map({1: "Hombre", 2: "Mujer"})
d["e_con"]  = d.e_con.map({1:"Unión libre",2:"Separado",3:"Divorciado",4:"Viudo",5:"Casado",6:"Soltero"})
d["t_loc"]  = d.t_loc_tri.map({1:">100 mil hab.",2:"15 mil–100 mil",3:"2.5 mil–15 mil",4:"<2.5 mil hab."})
d["rama"]   = d.rama.map({6:"Agropecuario",1:"Construcción",2:"Manufactura",3:"Comercio",4:"Servicios",5:"Otros"})
d["ent"]    = d.cve_ent.map(ENT)
print(f"Nulos tras recodificar -> anios_esc: {d.anios_esc.isna().sum():,} | hrsocup: {d.hrsocup.isna().sum():,} | "
      f"ingreso: {d.ingocup_c.isna().sum():,} | e_con: {d.e_con.isna().sum():,} | rama: {d.rama.isna().sum():,}")
""")
md(r"""
### 2.3 Valores atípicos
El ingreso tiene una cola derecha muy larga (unos pocos ingresos enormes). Usamos la regla del rango intercuartílico (IQR) **solo para detectar**, y para el modelo aplicamos **winsorización al percentil 99** (calculado con entrenamiento) más **transformación `log1p`**. Winsorizar conserva la fila y evita que pocos valores extremos dominen a la regresión logística.
""")
code(r"""
def iqr_atipicos(s):
    s = s.dropna(); q1, q3 = s.quantile([.25, .75]); lim = q3 + 1.5 * (q3 - q1)
    return int((s > lim).sum()), float(lim)
at = {}
for c in ["ingocup_c", "hrsocup", "eda"]:
    n_at, lim = iqr_atipicos(d[c]); at[c] = {"atipicos": n_at, "limite_iqr": lim, "pct": 100 * n_at / d[c].notna().sum()}
R["atipicos"] = at; display(pd.DataFrame(at).T.round(2))

fig, ax = plt.subplots(1, 3, figsize=(12, 3.4))
p99 = d.ingocup_c.quantile(.99)
ax[0].hist(d.ingocup_c.dropna(), bins=60, color=AZUL); ax[0].axvline(p99, color=ROJO, ls="--", label=f"p99 = ${p99:,.0f}")
ax[0].set_title("Ingreso mensual (original)"); ax[0].legend()
ax[1].hist(np.log1p(d.ingocup_c.clip(upper=p99).dropna()), bins=60, color=VERDE); ax[1].set_title("Ingreso: winsorizado + log1p")
ax[2].boxplot([d.hrsocup.dropna()], flierprops=dict(markersize=2, alpha=.3)); ax[2].set_xticks([1]); ax[2].set_xticklabels(["Horas por semana"])
ax[2].set_title("Horas trabajadas (cajas y atípicos)")
guardar("f03_outliers")
""")
md(r"""
### 2.4 Partición entrenamiento / prueba y preprocesamiento
Primero **separamos** (80 % entrenamiento, 20 % prueba, estratificado por la variable objetivo) y después calculamos todo lo que *aprende* de los datos (topes del p99, medianas, medias y desviaciones) **solo con entrenamiento**. Así la prueba simula datos nuevos.

**Transformación de cualitativas a cuantitativas:**
- *One-Hot Encoding* para variables nominales (sexo, estado conjugal, tamaño de localidad, sector, entidad).
- Variable binaria `sin_ingreso` (0/1).
- Escolaridad ya viene como número (años aprobados), por lo que no necesita codificación; `niv_ins` y `cs_p13_1` se descartan por redundancia (ver sección 3).

**Estandarización** (media 0, desviación 1): solo para la regresión logística, porque su penalización y optimización dependen de la escala. Los árboles y *boosting* son invariantes a escala, así que no la necesitan.
""")
code(r"""
NUM = ["eda", "anios_esc", "hrsocup", "ing_log"]
BIN = ["sin_ingreso"]
CAT = ["sex", "e_con", "t_loc", "rama", "ent"]
FEATURES = NUM + BIN + CAT

tr_idx, te_idx = train_test_split(d.index, test_size=.20, stratify=d.y, random_state=SEED)
topes = {"ingocup_c": float(d.loc[tr_idx, "ingocup_c"].quantile(.99)),
         "hrsocup":   float(d.loc[tr_idx, "hrsocup"].quantile(.99))}       # solo con entrenamiento

def preparar(df):
    # Aplica los topes (winsorización) y la transformación log; deja NaN para imputar en el pipeline
    X = df.copy()
    X["ing_log"]  = np.log1p(X.ingocup_c.clip(upper=topes["ingocup_c"]))
    X["hrsocup"]  = X.hrsocup.clip(upper=topes["hrsocup"])
    X[CAT] = X[CAT].astype(object).where(X[CAT].notna(), np.nan)
    return X[FEATURES]

X_tr, X_te = preparar(d.loc[tr_idx]), preparar(d.loc[te_idx])
y_tr, y_te = d.loc[tr_idx, "y"], d.loc[te_idx, "y"]
R.update(n_train=len(X_tr), n_test=len(X_te), topes=topes)
print(f"Entrenamiento: {len(X_tr):,} | Prueba: {len(X_te):,} | % informal train {y_tr.mean():.1%} / test {y_te.mean():.1%}")

def hacer_pre(escalar=True):
    num = [("imp", SimpleImputer(strategy="median"))] + ([("sc", StandardScaler())] if escalar else [])
    cat = Pipeline([("imp", SimpleImputer(strategy="constant", fill_value="No especificado")),
                    ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    return ColumnTransformer([("num", Pipeline(num), NUM), ("bin", "passthrough", BIN), ("cat", cat, CAT)])
""")
md(r"""
### 2.5 Original vs procesado y verificación de que no se distorsionó la información
Comparamos las distribuciones **antes** (valores originales observados) y **después** (winsorizado + imputado) y revisamos que la relación de cada variable con la variable objetivo se conserve.
""")
code(r"""
pre_demo = hacer_pre(escalar=False).fit(X_tr)
Xp = pd.DataFrame(pre_demo.transform(X_tr), columns=pre_demo.get_feature_names_out(), index=X_tr.index)

rows = []
orig = {"eda": d.loc[tr_idx,"eda"], "anios_esc": d.loc[tr_idx,"anios_esc"], "hrsocup": d.loc[tr_idx,"hrsocup"],
        "ing_log": np.log1p(d.loc[tr_idx,"ingocup_c"])}
for c in NUM:
    a, b = orig[c].dropna(), Xp[f"num__{c}"]
    ks = stats.ks_2samp(a, b).statistic
    ry_a = np.corrcoef(a, y_tr.loc[a.index])[0, 1]; ry_b = np.corrcoef(b, y_tr)[0, 1]
    rows.append({"Variable": c, "Media original": a.mean(), "Media procesada": b.mean(), "Mediana original": a.median(),
                 "Mediana procesada": b.median(), "KS": ks, "Corr. con y (orig.)": ry_a, "Corr. con y (proc.)": ry_b})
verif = pd.DataFrame(rows).round(3); R["verificacion"] = verif.to_dict("records"); display(verif)

comp = pd.DataFrame({"": ["Original (SDEM completa)", "Procesado (X entrenamiento)"],
                     "Filas": [raw.shape[0], Xp.shape[0]], "Columnas": [raw.shape[1], Xp.shape[1]],
                     "Valores nulos": [int(raw.isna().sum().sum()), int(Xp.isna().sum().sum())]})
R["orig_vs_proc"] = comp.to_dict("records"); display(comp)

fig, ax = plt.subplots(1, 4, figsize=(14, 3))
for a_, c, t in zip(ax, NUM, ["Edad", "Años de escolaridad", "Horas por semana", "log(1 + ingreso)"]):
    a_.hist(orig[c].dropna(), bins=35, alpha=.55, color=GRIS, density=True, label="original")
    a_.hist(Xp[f"num__{c}"], bins=35, alpha=.55, color=AZUL, density=True, label="procesado"); a_.set_title(t)
ax[0].legend(); guardar("f04_antes_despues")
""")

# ───────────────────────────── 3 ─────────────────────────────
md(r"""
## 3. Identificación y clasificación de variables

| Rol | Variable | Tipo | Justificación |
|---|---|---|---|
| **y** | `emp_ppal` → `y` (1 informal, 0 formal) | cualitativa binaria | medición oficial de informalidad |
| X | `eda` (edad) | cuantitativa | el ciclo de vida afecta la inserción laboral |
| X | `anios_esc` (años de escolaridad) | cuantitativa | capital humano (H1) |
| X | `hrsocup` (horas por semana) | cuantitativa | intensidad del trabajo |
| X | `ing_log` (log del ingreso) | cuantitativa | remuneración (H3) |
| X | `sin_ingreso` | binaria | trabajo no remunerado |
| X | `sex`, `e_con` | cualitativa | brechas de género y hogar |
| X | `t_loc` (tamaño de localidad) | cualitativa ordinal | urbano vs rural (H2) |
| X | `rama` (sector de actividad) | cualitativa nominal | cada sector tiene distinta formalización |
| X | `ent` (entidad federativa) | cualitativa nominal | diferencias regionales |

### 3.1 Relación estadística entre cada variable y la variable objetivo
""")
code(r"""
dd = d.loc[d.index].copy(); dd["ing_log"] = np.log1p(dd.ingocup_c)
def cramers_v(x, y):
    t = pd.crosstab(x, y); chi2, p, _, _ = stats.chi2_contingency(t)
    n = t.values.sum(); k = min(t.shape) - 1
    return np.sqrt(chi2 / (n * k)), p
res = []
for c in CAT:
    v, p = cramers_v(dd[c].fillna("No especificado"), dd.y); res.append({"Variable": c, "Prueba": "χ² (Cramér V)", "Tamaño de efecto": v, "p-value": p})
res.append({"Variable": "sin_ingreso", "Prueba": "χ² (Cramér V)", **dict(zip(["Tamaño de efecto","p-value"], cramers_v(dd.sin_ingreso, dd.y)))})
for c in NUM:
    a, b = dd.loc[dd.y==1, c].dropna(), dd.loc[dd.y==0, c].dropna()
    dco = (a.mean() - b.mean()) / np.sqrt((a.var() + b.var()) / 2)
    res.append({"Variable": c, "Prueba": "Mann-Whitney (d de Cohen)", "Tamaño de efecto": abs(dco), "p-value": stats.mannwhitneyu(a, b).pvalue})
assoc = pd.DataFrame(res).sort_values("Tamaño de efecto", ascending=False)
R["asociacion"] = assoc.to_dict("records"); display(assoc.round(4))

fig, ax = plt.subplots(figsize=(7.5, 3.8))
ax.barh(assoc["Variable"][::-1], assoc["Tamaño de efecto"][::-1], color=AZUL)
ax.set_title("Fuerza de asociación con la informalidad (Cramér V o |d|)"); ax.grid(False)
guardar("f07_asociacion")
""")
code(r"""
# Gráficas descriptivas: tasa de informalidad por grupos (todas con la muestra de estudio)
dd["esc_gr"] = pd.cut(dd.anios_esc, [-1, 0, 6, 9, 12, 16, 30], labels=["0", "1–6", "7–9", "10–12", "13–16", "17+"])
dd["eda_gr"] = pd.cut(dd.eda, [14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 98], labels=["15–19","20–24","25–29","30–34","35–39","40–44","45–49","50–54","55–59","60–64","65+"])
def tasa(col): return dd.groupby(col, observed=True).y.mean() * 100
fig, ax = plt.subplots(2, 3, figsize=(14, 7))
for a_, col, t in zip(ax.ravel(), ["esc_gr","eda_gr","t_loc","rama","sex","e_con"],
                      ["Años de escolaridad","Edad","Tamaño de localidad","Sector de actividad","Sexo","Estado conjugal"]):
    s = tasa(col); s = s.sort_values() if col in ["rama","e_con"] else s
    a_.bar(s.index.astype(str), s.values, color=AZUL); a_.axhline(100*dd.y.mean(), color=NARANJA, ls="--", lw=1)
    a_.set_title(f"% informal por {t.lower()}"); a_.tick_params(axis="x", rotation=40); a_.set_ylim(0, 100)
guardar("f05_tasas_grupo")
R["tasas"] = {c: tasa(c).round(1).to_dict() for c in ["esc_gr","eda_gr","t_loc","rama","sex"]}

ent_t = tasa("ent").sort_values()
fig, ax = plt.subplots(figsize=(8, 8)); ax.barh(ent_t.index, ent_t.values, color=[ROJO if v > 60 else AZUL for v in ent_t.values])
ax.axvline(100*dd.y.mean(), color=NARANJA, ls="--"); ax.set_title("% de ocupados en informalidad por entidad"); ax.grid(False)
guardar("f06_entidades"); R["ent_top"] = ent_t.tail(3).round(1).to_dict(); R["ent_bottom"] = ent_t.head(3).round(1).to_dict()
""")
md(r"""
### 3.2 Variables redundantes
`niv_ins` (nivel de instrucción) y `cs_p13_1` (escolaridad) miden lo mismo que `anios_esc`. Dejar las tres sería redundante (multicolinealidad). También `ur` (urbano/rural) repite `t_loc`.
""")
code(r"""
cor = dd[["anios_esc", "niv_ins", "cs_p13_1", "eda", "hrsocup", "ing_log", "y"]].replace({99: np.nan}).corr(method="spearman")
R["cor_redundantes"] = {"anios_esc~niv_ins": float(cor.loc["anios_esc","niv_ins"]), "anios_esc~cs_p13_1": float(cor.loc["anios_esc","cs_p13_1"])}
fig, ax = plt.subplots(figsize=(6.2, 5))
sns.heatmap(cor, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1, ax=ax, cbar_kws={"shrink": .8}); ax.grid(False)
ax.set_title("Correlación de Spearman"); guardar("f08_correlacion")
print("Correlación de anios_esc con niv_ins y cs_p13_1:", {k: round(v, 2) for k, v in R["cor_redundantes"].items()})
""")
md(r"""
### 3.3 Prueba de **fuga de información** (*data leakage*)
INEGI define la informalidad a partir de la **posición en la ocupación**, el **tamaño de la unidad económica**, el **tipo de unidad** y el **acceso a la seguridad social**. Esas variables *construyen* la respuesta, así que si las usáramos como predictoras el modelo "adivinaría" la etiqueta por definición. Lo comprobamos con un modelo rápido (gradient boosting) con y sin esas variables.
""")
code(r"""
FUGA = {"seg_soc": "acceso a seguridad social", "pos_ocu": "posición en la ocupación", "emple7c": "tamaño de la unidad",
        "tue_ppal": "tipo de unidad económica", "sec_ins": "sector institucional"}
def auc_sin_fuga():
    num_cat = lambda idx: pd.concat([preparar(d.loc[idx]).drop(columns=CAT).reset_index(drop=True),
        pd.get_dummies(d.loc[idx, ["sex","t_loc","rama","e_con"]].fillna("ND"), dtype=int).reset_index(drop=True)], axis=1)
    a, b = num_cat(tr_idx), num_cat(te_idx); b = b.reindex(columns=a.columns, fill_value=0)
    m = HistGradientBoostingClassifier(random_state=SEED).fit(a, y_tr.values)
    return roc_auc_score(y_te.values, m.predict_proba(b)[:, 1]), a.columns.tolist()
base, cols_base = auc_sin_fuga()
def con(extra):
    mk = lambda idx: pd.concat([preparar(d.loc[idx]).drop(columns=CAT).reset_index(drop=True),
        pd.get_dummies(d.loc[idx, ["sex","t_loc","rama","e_con"]].fillna("ND"), dtype=int).reset_index(drop=True),
        d.loc[idx, extra].reset_index(drop=True)], axis=1)
    a, b = mk(tr_idx), mk(te_idx); b = b.reindex(columns=a.columns, fill_value=0)
    return roc_auc_score(y_te.values, HistGradientBoostingClassifier(random_state=SEED).fit(a, y_tr.values).predict_proba(b)[:, 1])
fuga = {"Sin variables definitorias (nuestro modelo)": base}
for k, v in FUGA.items(): fuga[f"+ {k} ({v})"] = con([k])
fuga["+ las 5 variables definitorias"] = con(list(FUGA))
R["fuga"] = fuga
fg = pd.Series(fuga); display(fg.round(4).to_frame("ROC-AUC en prueba"))

fig, ax = plt.subplots(figsize=(9, 3.8))
ax.barh(fg.index[::-1], fg.values[::-1], color=[ROJO if v > .95 else AZUL for v in fg.values[::-1]])
for i, v in enumerate(fg.values[::-1]): ax.text(v, i, f" {v:.3f}", va="center")
ax.set_xlim(.5, 1.05); ax.set_title("Fuga de información: AUC se dispara al incluir variables definitorias"); ax.grid(False)
guardar("f09_fuga")
print("Conclusión: las variables definitorias se EXCLUYEN del modelo final.")
""")

# ───────────────────────────── 4 ─────────────────────────────
md(r"""
## 4. Modelos de aprendizaje automático

**Tipo de problema:** clasificación supervisada binaria (informal = 1).

**Por qué estos algoritmos (de simple a complejo):**
- **Regresión logística** — línea base interpretable (razones de momios).
- **Árbol de decisión** — reglas legibles, captura no linealidades e interacciones.
- **Random Forest** — promedia muchos árboles (reduce varianza/sobreajuste).
- **HistGradientBoosting** — árboles en secuencia que corrigen errores del anterior; suele ser el mejor en datos tabulares y es muy eficiente en tiempo.
- **DummyClassifier** — línea base trivial (predice la clase mayoritaria) para comprobar que los modelos aportan algo.

**División y validación.** 80 % entrenamiento / 20 % prueba estratificado. Los hiperparámetros se buscan con **validación cruzada estratificada de 5 pliegues** sobre una submuestra de entrenamiento de 30,000 filas (para acotar el costo de cómputo) y, con los mejores parámetros, se **reentrena con todo el entrenamiento**. La prueba se usa **una sola vez**. El mejor modelo se elige por AUC de validación cruzada, **no** por la prueba.

**Métricas:** accuracy, precision, recall, F1, ROC-AUC (calidad de ordenamiento, independiente del umbral) y PR-AUC.
""")
code(r"""
# Balance de clases y efecto de class_weight (regresión logística)
bal = y_tr.value_counts(normalize=True).rename({1: "Informal", 0: "Formal"}); R["balance"] = bal.to_dict()
pre_lr_demo = hacer_pre(True)
def prueba_cw(cw):
    m = Pipeline([("pre", hacer_pre(True)), ("clf", LogisticRegression(max_iter=1000, class_weight=cw))]).fit(X_tr, y_tr)
    p = m.predict(X_te); return {"class_weight": str(cw), "precision": precision_score(y_te, p), "recall": recall_score(y_te, p), "F1": f1_score(y_te, p)}
cwt = pd.DataFrame([prueba_cw(None), prueba_cw("balanced")]).round(4); R["class_weight"] = cwt.to_dict("records"); display(cwt)
fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
ax[0].bar(bal.index, bal.values * 100, color=[AZUL, NARANJA]); ax[0].set_title("Distribución de la variable objetivo (%)"); ax[0].set_ylim(0, 100)
for i, v in enumerate(bal.values): ax[0].text(i, v * 100 + 1, f"{v:.1%}", ha="center")
cwt.set_index("class_weight")[["precision", "recall", "F1"]].plot.bar(ax=ax[1], color=[AZUL, NARANJA, VERDE], rot=0)
ax[1].set_title("Regresión logística: efecto de class_weight"); ax[1].set_ylim(.6, .9); ax[1].legend(loc="lower right")
guardar("f10_balance")
""")
code(r"""
# Submuestra de entrenamiento para la búsqueda de hiperparámetros (costo acotado)
sub = X_tr.sample(30000, random_state=SEED).index
Xs, ys = X_tr.loc[sub], y_tr.loc[sub]
cv5 = StratifiedKFold(5, shuffle=True, random_state=SEED)

MODELOS = {
  "Regresión logística": dict(escalar=True, modelo=LogisticRegression(max_iter=1000), busqueda="grid",
      grid={"clf__C": [0.01, 0.1, 1, 10], "clf__class_weight": [None, "balanced"]}),
  "Árbol de decisión": dict(escalar=False, modelo=DecisionTreeClassifier(random_state=SEED), busqueda="random", n_iter=12,
      grid={"clf__max_depth": [3, 5, 8, 12, 16], "clf__min_samples_leaf": [20, 50, 100], "clf__criterion": ["gini", "entropy"]}),
  "Random Forest": dict(escalar=False, modelo=RandomForestClassifier(random_state=SEED), busqueda="random", n_iter=8,
      grid={"clf__n_estimators": [150, 300], "clf__max_depth": [10, 16, None], "clf__min_samples_leaf": [5, 20],
            "clf__max_features": ["sqrt", 0.5]}),
  "HistGradientBoosting": dict(escalar=False, modelo=HistGradientBoostingClassifier(random_state=SEED, early_stopping=True,
                                                                                    n_iter_no_change=15), busqueda="random", n_iter=12,
      grid={"clf__learning_rate": [0.03, 0.05, 0.1, 0.2], "clf__max_leaf_nodes": [15, 31, 63], "clf__max_iter": [200, 400],
            "clf__l2_regularization": [0, 1, 10], "clf__min_samples_leaf": [20, 50]}),
}

def metricas(y, p, prob):
    return {"accuracy": accuracy_score(y, p), "precision": precision_score(y, p), "recall": recall_score(y, p),
            "F1": f1_score(y, p), "ROC-AUC": roc_auc_score(y, prob), "PR-AUC": average_precision_score(y, prob)}

resultados, ajustados, params = {}, {}, {}

# Línea base
t = time.time(); dm = Pipeline([("pre", hacer_pre(False)), ("clf", DummyClassifier(strategy="prior"))]).fit(X_tr, y_tr)
pr = dm.predict_proba(X_te)[:, 1]
resultados["Línea base (clase mayoritaria)"] = {**metricas(y_te, dm.predict(X_te), pr), "AUC train": .5, "AUC CV": .5,
                                                "t_busqueda": 0, "t_fit": time.time() - t, "t_pred_10k": 0}

for nombre, cfg in MODELOS.items():
    pipe = Pipeline([("pre", hacer_pre(cfg["escalar"])), ("clf", cfg["modelo"])])
    t0 = time.time()
    if cfg["busqueda"] == "grid":
        s = GridSearchCV(pipe, cfg["grid"], scoring="roc_auc", cv=cv5, n_jobs=-1, refit=False)
    else:
        s = RandomizedSearchCV(pipe, cfg["grid"], n_iter=cfg["n_iter"], scoring="roc_auc", cv=cv5, n_jobs=-1,
                               random_state=SEED, refit=False)
    s.fit(Xs, ys); t_busq = time.time() - t0
    mejor = clone(pipe).set_params(**s.best_params_)
    if nombre == "Random Forest": mejor.set_params(clf__n_jobs=-1)
    t0 = time.time(); mejor.fit(X_tr, y_tr); t_fit = time.time() - t0
    t0 = time.time(); prob = mejor.predict_proba(X_te)[:, 1]; t_pred = (time.time() - t0) * 10000 / len(X_te)
    resultados[nombre] = {**metricas(y_te, (prob >= .5).astype(int), prob),
        "AUC train": roc_auc_score(y_tr, mejor.predict_proba(X_tr)[:, 1]), "AUC CV": float(s.best_score_),
        "t_busqueda": t_busq, "t_fit": t_fit, "t_pred_10k": t_pred}
    ajustados[nombre], params[nombre] = mejor, {k.replace("clf__", ""): v for k, v in s.best_params_.items()}
    print(f"{nombre:22s} AUC CV={s.best_score_:.4f} | AUC prueba={resultados[nombre]['ROC-AUC']:.4f} | búsqueda {t_busq:5.1f}s | fit {t_fit:5.1f}s | {params[nombre]}")

tab = pd.DataFrame(resultados).T
tab["Brecha train–test"] = tab["AUC train"] - tab["ROC-AUC"]
R["modelos"] = tab.round(5).to_dict("index"); R["mejores_params"] = {k: {a: (None if v is None else v if isinstance(v,(str,int,float)) else str(v)) for a, v in p.items()} for k, p in params.items()}
display(tab[["accuracy","precision","recall","F1","ROC-AUC","PR-AUC","AUC CV","AUC train","Brecha train–test"]].round(4))
""")
code(r"""
nombres = list(ajustados)
mejor_nombre = max(nombres, key=lambda n: resultados[n]["AUC CV"])          # se elige por validación cruzada
mejor = ajustados[mejor_nombre]; R["mejor_modelo"] = mejor_nombre
probs = {n: ajustados[n].predict_proba(X_te)[:, 1] for n in nombres}
colores = dict(zip(nombres, [GRIS, VERDE, NARANJA, AZUL]))
print("Mejor modelo (por AUC de validación cruzada):", mejor_nombre)

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for n in nombres:
    fpr, tpr, _ = roc_curve(y_te, probs[n]); ax[0].plot(fpr, tpr, color=colores[n], lw=2, label=f"{n} (AUC={resultados[n]['ROC-AUC']:.3f})")
    p_, r_, _ = precision_recall_curve(y_te, probs[n]); ax[1].plot(r_, p_, color=colores[n], lw=2, label=f"{n} (AP={resultados[n]['PR-AUC']:.3f})")
ax[0].plot([0, 1], [0, 1], "k--", lw=1); ax[0].set(xlabel="Tasa de falsos positivos", ylabel="Tasa de verdaderos positivos", title="Curva ROC (prueba)"); ax[0].legend(loc="lower right", fontsize=8)
ax[1].set(xlabel="Recall", ylabel="Precision", title="Curva Precision–Recall (prueba)"); ax[1].legend(loc="lower left", fontsize=8)
guardar("f12_roc_pr")

mt = pd.DataFrame(resultados).T[["accuracy", "precision", "recall", "F1", "ROC-AUC"]].drop("Línea base (clase mayoritaria)")
ax = mt.plot.bar(figsize=(10, 3.8), rot=15, color=[GRIS, AZUL, NARANJA, VERDE, ROJO], width=.8)
ax.set_ylim(.6, .95); ax.set_title("Métricas en prueba por modelo"); ax.legend(ncol=5, loc="upper left", fontsize=8); guardar("f13_metricas")
""")
code(r"""
# Sobreajuste: AUC entrenamiento vs validación cruzada vs prueba, y curva de validación del árbol
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
x = np.arange(len(nombres)); w = .27
ax[0].bar(x - w, [resultados[n]["AUC train"] for n in nombres], w, label="Entrenamiento", color=GRIS)
ax[0].bar(x,     [resultados[n]["AUC CV"] for n in nombres],    w, label="Validación cruzada", color=NARANJA)
ax[0].bar(x + w, [resultados[n]["ROC-AUC"] for n in nombres],   w, label="Prueba", color=AZUL)
ax[0].set_xticks(x); ax[0].set_xticklabels([n.replace(" ", "\n") for n in nombres], fontsize=8); ax[0].set_ylim(.6, 1.0)
ax[0].set_title("Diagnóstico de sobreajuste (ROC-AUC)"); ax[0].legend(fontsize=8)
prof = [1, 2, 3, 5, 8, 12, 16, 24]
tr_s, va_s = validation_curve(Pipeline([("pre", hacer_pre(False)), ("clf", DecisionTreeClassifier(min_samples_leaf=20, random_state=SEED))]),
                              Xs, ys, param_name="clf__max_depth", param_range=prof, scoring="roc_auc", cv=3, n_jobs=-1)
ax[1].plot(prof, tr_s.mean(1), "o-", color=GRIS, label="Entrenamiento"); ax[1].plot(prof, va_s.mean(1), "o-", color=AZUL, label="Validación")
ax[1].set(xlabel="Profundidad máxima del árbol", ylabel="ROC-AUC", title="Curva de validación: árbol de decisión"); ax[1].legend()
guardar("f14_sobreajuste")
R["curva_validacion_dt"] = {"profundidad": prof, "train": tr_s.mean(1).round(4).tolist(), "val": va_s.mean(1).round(4).tolist()}

# Matriz de confusión del mejor modelo
fig, ax = plt.subplots(figsize=(4.6, 4))
pred = (probs[mejor_nombre] >= .5).astype(int); cm = confusion_matrix(y_te, pred)
ConfusionMatrixDisplay(cm, display_labels=["Formal", "Informal"]).plot(ax=ax, cmap="Blues", colorbar=False, values_format=",d"); ax.grid(False)
ax.set_title(f"Matriz de confusión: {mejor_nombre}"); guardar("f15_confusion"); R["confusion"] = cm.tolist()
""")

# ───────────────────────────── 5 ─────────────────────────────
md(r"""
## 5. Estructura, funcionamiento y eficiencia del programa

**Etapas del programa:** (1) descarga → (2) auditoría y limpieza → (3) partición → (4) `Pipeline` (imputación + codificación + escalado + modelo) → (5) búsqueda de hiperparámetros con validación cruzada → (6) evaluación en prueba → (7) interpretación.

**Instrucciones clave:**
- `train_test_split(..., stratify=y)`: conserva la proporción de clases en ambas partes.
- `Pipeline` + `ColumnTransformer`: encadenan transformaciones y modelo; garantizan que todo lo "aprendido" (medianas, medias, categorías) sale **solo de entrenamiento**.
- `RandomizedSearchCV(..., cv=StratifiedKFold(5))`: prueba combinaciones al azar de hiperparámetros con validación cruzada.
- `permutation_importance`: mide cuánto cae el AUC al barajar una variable.

### 5.1 Tiempos medidos y operaciones más costosas
""")
code(r"""
tt = pd.DataFrame(resultados).T[["t_busqueda", "t_fit", "t_pred_10k"]].astype(float).drop("Línea base (clase mayoritaria)")
tt.columns = ["Búsqueda de hiperparámetros (s)", "Ajuste final (s)", "Predicción por 10 mil filas (s)"]
R["tiempos"] = tt.round(3).to_dict("index"); display(tt.round(2))
ax = tt.iloc[:, :2].plot.bar(figsize=(8, 3.5), rot=15, color=[NARANJA, AZUL]); ax.set_title("Costo de cómputo por modelo (segundos)"); guardar("f16_tiempos")
mem_raw = raw.memory_usage(deep=True).sum() / 1e6
Xd = X_tr.copy(); Xd[NUM] = Xd[NUM].astype("float32"); Xd[BIN] = Xd[BIN].astype("int8"); Xd[CAT] = Xd[CAT].astype("category")
mem_x, mem_xd = X_tr.memory_usage(deep=True).sum() / 1e6, Xd.memory_usage(deep=True).sum() / 1e6
R["memoria"] = {"base_completa_MB": mem_raw, "X_train_MB": mem_x, "X_train_optimizado_MB": mem_xd}
print(f"Memoria base completa: {mem_raw:,.0f} MB | X_train: {mem_x:.1f} MB -> con tipos optimizados: {mem_xd:.1f} MB")
""")
md(r"""
### 5.2 Complejidad temporal (teoría y evidencia empírica)
*n* = número de filas, *p* = número de variables (tras One-Hot), *T* = número de árboles/iteraciones, *d* = profundidad, *b* = número de *bins* (255).

| Modelo | Entrenamiento | Predicción por muestra |
|---|---|---|
| Regresión logística (lbfgs) | O(n · p · iteraciones) | O(p) |
| Árbol de decisión | O(n · p · log n) | O(d) |
| Random Forest | O(T · √p · n · log n) | O(T · d) |
| HistGradientBoosting | O(T · n · p) (usa *histogramas*, no ordena) | O(T · d) |

Para comprobarlo medimos el tiempo de entrenamiento con distintos tamaños de muestra (un solo hilo) y estimamos la pendiente en escala log-log: pendiente ≈ 1 sugiere crecimiento lineal; algo mayor, *n log n*.
""")
code(r"""
tamanios = [5000, 10000, 20000, 40000, 80000, len(X_tr)]
esquema = {"Regresión logística": (True, LogisticRegression(max_iter=1000)),
           "Árbol de decisión": (False, DecisionTreeClassifier(max_depth=8, min_samples_leaf=20, random_state=SEED)),
           "Random Forest": (False, RandomForestClassifier(n_estimators=100, max_depth=12, min_samples_leaf=20, random_state=SEED, n_jobs=1)),
           "HistGradientBoosting": (False, HistGradientBoostingClassifier(max_iter=150, random_state=SEED))}
esc = {}
with threadpool_limits(limits=1):
    for n, (sc, m) in esquema.items():
        ts = []
        for k in tamanios:
            idx = X_tr.sample(k, random_state=SEED).index; p = Pipeline([("pre", hacer_pre(sc)), ("clf", clone(m))])
            t0 = time.time(); p.fit(X_tr.loc[idx], y_tr.loc[idx]); ts.append(time.time() - t0)
        esc[n] = ts
pend = {n: float(np.polyfit(np.log(tamanios), np.log(ts), 1)[0]) for n, ts in esc.items()}
R["escalamiento"] = {"n": tamanios, "tiempos": esc, "pendientes": pend}
fig, ax = plt.subplots(figsize=(7, 4.2))
for n, ts in esc.items(): ax.plot(tamanios, ts, "o-", color=colores[n], label=f"{n} (pendiente {pend[n]:.2f})")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set(xlabel="Filas de entrenamiento (n)", ylabel="Segundos", title="Escalamiento empírico del tiempo de entrenamiento"); ax.legend(fontsize=8)
guardar("f17_escalamiento"); print({k: round(v, 2) for k, v in pend.items()})
""")
md(r"""
### 5.3 Reproducibilidad y mejoras posibles
Verificamos que, con la misma semilla, el modelo vuelve a producir **exactamente** las mismas predicciones.

**Mejoras para optimizar:** (i) guardar el pipeline con `joblib` para no reentrenar; (ii) usar `HalvingRandomSearchCV` o Optuna para buscar hiperparámetros con menos cómputo; (iii) leer solo las columnas necesarias (`usecols`) y tipos `category`/`float32` para reducir memoria; (iv) separar el código en un módulo con funciones (`limpiar`, `construir_pipeline`, `evaluar`) y pruebas unitarias; (v) usar el factor de expansión como `sample_weight` para estimar a nivel población.
""")
code(r"""
m1 = clone(mejor).fit(X_tr, y_tr); m2 = clone(mejor).fit(X_tr, y_tr)
rep = bool(np.allclose(m1.predict_proba(X_te)[:, 1], m2.predict_proba(X_te)[:, 1]))
R["reproducible"] = rep; print("¿Mismas predicciones al reentrenar con la misma semilla?", rep)
""")

# ───────────────────────────── 6 ─────────────────────────────
md(r"""
## 6. Resultados, interpretación y conclusiones

### 6.1 ¿Qué variables importan? (importancia por permutación)
Barajamos una variable a la vez en el conjunto de prueba y medimos cuánto baja el AUC. Una caída grande = la variable es importante para el modelo.
""")
code(r"""
Xp_te = X_te.sample(15000, random_state=SEED); yp_te = y_te.loc[Xp_te.index]
pi = permutation_importance(mejor, Xp_te, yp_te, scoring="roc_auc", n_repeats=5, random_state=SEED, n_jobs=-1)
imp = pd.Series(pi.importances_mean, index=Xp_te.columns).sort_values(); err = pd.Series(pi.importances_std, index=Xp_te.columns)[imp.index]
R["importancia"] = imp.round(4).to_dict()
fig, ax = plt.subplots(figsize=(7.5, 4.2)); ax.barh(imp.index, imp.values, xerr=err.values, color=AZUL)
ax.set_xlabel("Caída del AUC al permutar"); ax.set_title(f"Importancia por permutación — {mejor_nombre}"); ax.grid(False); guardar("f18_importancia")
print(imp.sort_values(ascending=False).round(4).to_string())
""")
md(r"""
### 6.2 ¿Cómo cambia la predicción con cada variable? (dependencia parcial)
""")
code(r"""
fig, ax = plt.subplots(1, 4, figsize=(15, 3.4))
PartialDependenceDisplay.from_estimator(mejor, X_te.sample(4000, random_state=SEED), ["eda", "anios_esc", "hrsocup", "ing_log"],
                                        kind="average", grid_resolution=25, ax=ax, line_kw={"color": AZUL})
for a_, t in zip(ax, ["Edad", "Años de escolaridad", "Horas por semana", "log(1 + ingreso)"]): a_.set_xlabel(t); a_.set_ylabel("P(informal)")
plt.suptitle("Dependencia parcial de la probabilidad de informalidad", y=1.03, fontweight="bold"); guardar("f19_pdp")
""")
md(r"""
### 6.3 Contraste de hipótesis con regresión logística (razones de momios)
Ajustamos una regresión logística con `statsmodels` (da errores estándar e intervalos de confianza). Las numéricas están estandarizadas, así que su OR es **por cada +1 desviación estándar**. Las categorías se comparan contra una referencia (hombre, soltero, localidad > 100 mil hab., servicios, Jalisco).
""")
code(r"""
pre_sm = hacer_pre(True).fit(X_tr)
Xs_m = pd.DataFrame(pre_sm.transform(X_tr), columns=pre_sm.get_feature_names_out(), index=X_tr.index)
Xs_m.columns = [c.split("__", 1)[1] for c in Xs_m.columns]
ref = ["sex_Hombre", "e_con_Soltero", "t_loc_>100 mil hab.", "rama_Servicios", "ent_Jalisco"]
Xs_m = Xs_m.drop(columns=[c for c in ref if c in Xs_m.columns])
Xs_m = sm.add_constant(Xs_m.astype(float))
logit = sm.Logit(y_tr.values, Xs_m).fit(disp=0, maxiter=200)
ci = logit.conf_int()
OR = pd.DataFrame({"OR": np.exp(logit.params), "IC95_inf": np.exp(ci[0]), "IC95_sup": np.exp(ci[1]), "p": logit.pvalues}).drop("const")
OR.to_csv("resultados/odds_ratios.csv"); R["or"] = OR.round(4).to_dict("index")
R["pseudo_r2"] = float(logit.prsquared)
vis = OR.drop([i for i in OR.index if i.startswith("ent_")])
vis = vis.loc[vis.OR.sort_values().index]
fig, ax = plt.subplots(figsize=(8, 7))
ax.errorbar(vis.OR, range(len(vis)), xerr=[vis.OR - vis.IC95_inf, vis.IC95_sup - vis.OR], fmt="o", color=AZUL, ecolor=GRIS, capsize=2)
ax.axvline(1, color=ROJO, ls="--"); ax.set_yticks(range(len(vis))); ax.set_yticklabels(vis.index, fontsize=8); ax.set_xscale("log")
ax.set_xlabel("Razón de momios (escala log; IC 95 %)"); ax.set_title("Regresión logística: ¿qué aumenta o reduce la probabilidad de informalidad?"); guardar("f20_oddsratios")
display(vis.round(3))

h = lambda v: OR.loc[v]
H = {"H1 escolaridad": ("anios_esc", h("anios_esc")), "H2 localidad <2.5 mil hab.": ("t_loc_<2.5 mil hab.", h("t_loc_<2.5 mil hab.")),
     "H3 ingreso": ("ing_log", h("ing_log"))}
hip = []
for k, (v, r) in H.items():
    esperado = (r.OR < 1) if k in ("H1 escolaridad", "H3 ingreso") else (r.OR > 1)
    hip.append({"Hipótesis": k, "OR": r.OR, "IC95_inf": r.IC95_inf, "IC95_sup": r.IC95_sup, "p": r.p,
                "Veredicto": "RESPALDADA" if (esperado and r.p < .05 and not (r.IC95_inf <= 1 <= r.IC95_sup)) else "RECHAZADA"})
hip = pd.DataFrame(hip); R["hipotesis"] = hip.round(4).to_dict("records"); display(hip.round(4))
""")
md(r"""
### 6.4 Calibración y desempeño por grupos
Un buen modelo no solo ordena bien: sus probabilidades deben parecerse a las frecuencias reales. Comparamos la tasa observada y la predicha por escolaridad y por sector.
""")
code(r"""
cal = d.loc[X_te.index, ["anios_esc", "rama"]].copy(); cal["real"] = y_te.values; cal["pred"] = probs[mejor_nombre]
cal["esc"] = pd.cut(cal.anios_esc, [-1, 0, 6, 9, 12, 16, 30], labels=["0", "1–6", "7–9", "10–12", "13–16", "17+"])
fig, ax = plt.subplots(1, 3, figsize=(14, 3.6))
for a_, col, t in zip(ax[:2], ["esc", "rama"], ["escolaridad (años)", "sector"]):
    g = cal.groupby(col, observed=True)[["real", "pred"]].mean() * 100
    g.plot.bar(ax=a_, color=[AZUL, NARANJA], rot=30); a_.set_title(f"Real vs predicho por {t}"); a_.set_ylabel("% informal"); a_.legend(["Real", "Predicho"])
dec = pd.qcut(cal.pred, 10, duplicates="drop"); g = cal.groupby(dec, observed=True)[["real", "pred"]].mean()
ax[2].plot([0, 1], [0, 1], "k--", lw=1); ax[2].plot(g.pred, g.real, "o-", color=AZUL); ax[2].set(xlabel="Probabilidad predicha (decil)", ylabel="Frecuencia real", title="Curva de calibración")
guardar("f21_calibracion")
""")
code(r"""
# Resumen final + guardado de resultados para el reporte y la presentación
mj = resultados[mejor_nombre]
R["resumen"] = {"mejor": mejor_nombre, "auc_test": mj["ROC-AUC"], "auc_cv": mj["AUC CV"], "f1": mj["F1"], "accuracy": mj["accuracy"],
                "precision": mj["precision"], "recall": mj["recall"], "brecha": mj["AUC train"] - mj["ROC-AUC"]}
tab.round(5).to_csv("resultados/metricas_modelos.csv")
def _j(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.ndarray,)): return o.tolist()
    return str(o)
json.dump(R, open("resultados/resumen.json", "w"), ensure_ascii=False, indent=1, default=_j)
display(Markdown(f"### Resultado\nMejor modelo: **{mejor_nombre}**, ROC-AUC en prueba = **{mj['ROC-AUC']:.3f}**, F1 = **{mj['F1']:.3f}**, "
                 f"accuracy = **{mj['accuracy']:.3f}**. Brecha entrenamiento–prueba = {mj['AUC train']-mj['ROC-AUC']:.3f}."))
""")
md(r"""
### 6.5 Conclusiones, limitaciones y trabajo futuro
Las conclusiones detalladas (con las cifras de esta corrida) están en el documento del proyecto. En resumen: ver `resultados/resumen.json` y las tablas anteriores.

**Limitaciones.** (i) La ENOE es una encuesta con diseño muestral complejo; los modelos aquí se entrenaron **sin ponderar**, así que las probabilidades describen la muestra, no la población; (ii) se usa un solo trimestre (corte transversal); (iii) un modelo predictivo muestra *asociación*, no causalidad; (iv) se excluyen a propósito las variables que definen la informalidad.

**Trabajo futuro.** Usar varios trimestres y validación temporal, ponderar con `fac_tri`, probar XGBoost/LightGBM y calibración isotónica, y añadir variables contextuales (municipio, tamaño del hogar).
""")

nb = nbf.v4.new_notebook(); nb["cells"] = C
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                  "language_info": {"name": "python"}, "colab": {"provenance": []}}
nbf.write(nb, "/home/user/Polymarket-UP-DOWN-5m/proyecto_enoe/Proyecto_ENOE_Informalidad.ipynb")
print("notebook escrito:", len(C), "celdas")
