"""Diccionario de variables (se usa en el notebook, el documento y la presentacion)."""

# (nombre en mi codigo, nombre original en la ENOE, que significa, tipo, valores)
PRINCIPALES = [
    ("y", "emp_ppal", "Variable objetivo: 1 si la persona está en empleo informal, 0 si está en empleo formal", "Cualitativa binaria", "1 = informal, 0 = formal"),
    ("eda", "eda", "Edad de la persona en años cumplidos", "Cuantitativa", "15 a 98 años"),
    ("anios_esc", "anios_esc", "Años de escuela aprobados (0 = sin escuela, 12 = bachillerato, 17 o más = posgrado)", "Cuantitativa", "0 a 24; 99 = no especificado (lo cambié a NaN)"),
    ("hrsocup", "hrsocup", "Horas que trabaja a la semana en su ocupación", "Cuantitativa", "0 a 168; 0 = ausencia temporal (lo cambié a NaN)"),
    ("ingreso", "ingocup", "Ingreso mensual por su trabajo, en pesos", "Cuantitativa", "$0 a $250,000 (limitado al percentil 99 y con logaritmo)"),
    ("sin_ingreso", "ing7c (la creé)", "Vale 1 si la persona no recibe ingresos por su trabajo (ing7c = 6), 0 si sí recibe", "Cuantitativa binaria", "0 o 1"),
    ("sexo", "sex", "Sexo de la persona", "Cualitativa nominal", "Hombre, Mujer"),
    ("estado_civil", "e_con", "Situación conyugal", "Cualitativa nominal", "Soltero, Casado, Unión libre, Separado, Divorciado, Viudo"),
    ("localidad", "t_loc_tri", "Tamaño de la localidad donde vive", "Cualitativa ordinal", "Menos de 2.5 mil, 2.5 mil a 15 mil, 15 mil a 100 mil, Más de 100 mil habitantes"),
    ("sector", "rama", "Sector de actividad económica donde trabaja", "Cualitativa nominal", "Agropecuario, Construcción, Manufactura, Comercio, Servicios, Otros"),
    ("entidad", "cve_ent", "Estado de la República donde vive", "Cualitativa nominal", "32 entidades"),
]

# Variables que revisé pero NO usé como predictoras
OTRAS = [
    ("clase2", "Condición de actividad (1 = población ocupada); la usé para filtrar a las personas que trabajan", "Filtro"),
    ("fac_tri", "Factor de expansión trimestral: cuántas personas de la población representa cada registro. Lo usé solo para calcular la tasa de informalidad ponderada", "Comprobación"),
    ("niv_ins", "Nivel de instrucción (primaria, secundaria, medio superior y superior)", "Redundante con anios_esc (corr. 0.92)"),
    ("cs_p13_1", "Nivel de escolaridad que cursó (ninguno, primaria, secundaria, licenciatura, etc.)", "Redundante con anios_esc (corr. 0.98)"),
    ("ing7c", "Ingreso en grupos de salarios mínimos; 6 = no recibe ingresos y 7 = no especificado", "Solo para limpiar el ingreso"),
    ("seg_soc", "Acceso a servicios médicos como prestación del trabajo", "Fuga de información (define la informalidad)"),
    ("pos_ocu", "Posición en la ocupación (subordinado, empleador, por cuenta propia, sin pago)", "Fuga de información"),
    ("emple7c", "Tamaño de la unidad económica (cuántas personas trabajan en el negocio)", "Fuga de información"),
]
