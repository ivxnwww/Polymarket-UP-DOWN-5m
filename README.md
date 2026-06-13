# BTCUSD Polymarket 5m — modelos matemáticos, señales y estructura del proyecto

Este proyecto convierte los scripts crudos de observación en una arquitectura modular para analizar mercados de **BTC Up/Down 5m** de Polymarket usando BTC/USD como subyacente.

> **Importante:** este repositorio no ejecuta compras ni ventas. Calcula probabilidad, edge, riesgo de reversión y métricas de salida para que un bot externo o una interfaz visual puedan consumirlas. No es asesoría financiera.

---

## 1. Objetivo del sistema

El mercado `BTC Up/Down 5m` paga `1.00` si BTC cierra arriba del precio de referencia `K` y paga `0.00` si cierra abajo.

La pregunta matemática central es:

```text
p_UP = P(S_T > K | información actual)
```

Donde:

| Símbolo | Variable en código | Significado |
|---|---|---|
| `S_t` | `clean_price` | Precio actual estimado de BTC/USD |
| `K` | `strike_price` | Precio a superar en Polymarket |
| `T` | cierre de ronda | Tiempo de settlement de la ronda |
| `τ` | `seconds_remaining` | Segundos restantes para el cierre |
| `σ` | `sigma_per_sqrt_second` | Volatilidad de retornos logarítmicos por raíz de segundo |
| `p_UP` | `p_up_final` | Probabilidad estimada de que gane UP |
| `q_UP` | `up_ask` o `up_bid` | Precio del contrato UP en Polymarket |
| `edge` | `edge_buy_up`, `edge_buy_down` | Diferencia entre probabilidad estimada y precio de mercado |

---

## 2. Arquitectura propuesta

Los scripts originales estaban orientados a imprimir datos. La arquitectura nueva separa:

```text
Coinbase WebSocket
        ↓
BtcTick normalizado
        ↓
SharedMarketState ─────────────┐
                                ↓
Polymarket Page Scraper → strike, tiempo restante
                                ↓
Polymarket CLOB WebSocket → bids, asks, spread, mid
                                ↓
SignalEngine
        ├── EWMA volatility
        ├── Kalman filter
        ├── Brownian / Lognormal probability
        ├── Z-score dinámico
        ├── First-passage / reversal probability
        ├── Expected value vs Polymarket
        └── Optimal stopping para salida
                                ↓
Dashboard / bot externo / dataset para ML
```

La interfaz visual puede actualizarse cada `200 ms`, pero el modelo no debe depender de lo que se ve en pantalla. El modelo usa el último estado normalizado.

---

## 3. Estructura de archivos

```text
btc5m_polymarket_model/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── main.py
│
├── src/btc5m/
│   ├── coinbase_feed.py        # WebSocket Coinbase → BtcTick
│   ├── polymarket_market.py    # REST + WebSocket CLOB → OutcomeBook
│   ├── polymarket_page.py      # Playwright → strike, precio actual, tiempo restante
│   ├── state.py                # SharedMarketState y MarketSnapshot
│   ├── models.py               # Modelos matemáticos puros
│   ├── signal_engine.py        # Combina modelos y genera señales
│   ├── ml_dataset.py           # Exporta features para entrenar modelos
│   └── ml_train_logistic.py    # Entrenamiento base de regresión logística calibrada
│
└── data/
```

---

## 4. Instalación

Desde PowerShell, dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
pip install -e .
```

Ejecutar monitor:

```powershell
btc5m-monitor --display-interval 0.2
```

O con Python:

```powershell
python main.py --display-interval 0.2
```

Si quieres pasar una URL exacta de Polymarket:

```powershell
python main.py --market-url "https://polymarket.com/es/event/btc-updown-5m-1781297700"
```

Para evaluar una posición abierta, por ejemplo compraste UP a `0.50`:

```powershell
python main.py --position-side UP --entry-price 0.50 --quantity 100 --display-interval 0.2
```

---

## 5. Datos de entrada

### 5.1 Coinbase: precio y latencia

Archivo:

```text
src/btc5m/coinbase_feed.py
```

Coinbase produce:

```python
BtcTick(
    price=63280.43,
    exchange_time=...,   # tiempo del exchange
    received_at=...,     # tiempo de tu PC al recibirlo
)
```

Variables derivadas:

```text
exchange_latency_ms = received_at - exchange_time
data_age_ms = now - received_at
```

¿Por qué importa?

- `exchange_latency_ms` mide cuánto tardó en llegarte el dato desde el exchange.
- `data_age_ms` mide qué tan viejo es el último dato disponible.
- La latencia no predice dirección, pero reduce confianza. Por eso el motor acerca la probabilidad a `0.50` cuando el dato está viejo.

---

### 5.2 Polymarket Page: strike y tiempo restante

Archivo:

```text
src/btc5m/polymarket_page.py
```

Extrae:

```python
PageMarketData(
    current_price=...,        # precio visible de BTC en Polymarket
    strike_price=...,         # precio a superar K
    seconds_remaining=...,    # tiempo restante τ
)
```

¿Por qué va aquí?

El cálculo de probabilidad necesita saber si BTC debe cerrar arriba o abajo de `K`. Sin `K` no hay mercado binario que modelar.

---

### 5.3 Polymarket CLOB: bid, ask, spread y order book

Archivo:

```text
src/btc5m/polymarket_market.py
```

Produce libros normalizados:

```python
OutcomeBook(
    outcome="UP",
    bids=[...],
    asks=[...]
)
```

Variables derivadas:

```text
best_bid = mejor precio al que puedes vender
best_ask = mejor precio al que puedes comprar
spread = best_ask - best_bid
mid = (best_bid + best_ask) / 2
order_book_imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
```

¿Por qué importa?

El modelo puede decir `p_UP = 0.58`, pero eso no significa comprar siempre. Solo hay edge si el precio de compra es menor que tu probabilidad ajustada:

```text
edge_UP = p_UP - ask_UP
```

---

## 6. Modelos implementados

Los modelos están en:

```text
src/btc5m/models.py
```

El motor que los conecta está en:

```text
src/btc5m/signal_engine.py
```

---

# Modelo 1 — EWMA Volatility

La volatilidad es una de las variables más importantes porque define cuánto puede moverse BTC antes del cierre.

Retorno logarítmico:

```text
r_t = ln(S_t / S_{t-1})
```

Con ticks irregulares:

```text
var_inst = r_t² / Δt
```

EWMA:

```text
σ_t² = λσ_{t-1}² + (1 - λ) var_inst
```

En código:

```python
EWMAVolatility(lam=0.94)
```

Interpretación:

| `λ` | Efecto |
|---:|---|
| 0.90 | Reacciona rápido, más ruidoso |
| 0.94 | Balance inicial razonable |
| 0.97 | Más estable, reacciona lento |
| 0.99 | Muy lento para 5 minutos |

¿Por qué esta variable va antes de la probabilidad?

Porque la probabilidad terminal necesita `σ`. Sin volatilidad, no puedes comparar correctamente estar `$20` arriba faltando 3 minutos contra estar `$20` arriba faltando 10 segundos.

---

# Modelo 2 — Brownian / Lognormal Terminal Probability

Modelo base para calcular:

```text
P(S_T > K)
```

Se asume que el precio sigue un proceso lognormal de corto plazo:

```text
ln(S_T / S_t) ~ N((μ - 0.5σ²)τ, σ²τ)
```

Por lo tanto:

```text
p_UP = Φ((ln(S_t / K) + (μ - 0.5σ²)τ) / (σ√τ))
```

Para 5 minutos normalmente se puede empezar con:

```text
μ ≈ 0
```

Entonces:

```text
p_UP ≈ Φ((ln(S_t / K) - 0.5σ²τ) / (σ√τ))
```

En código:

```python
terminal_probability_up(price, strike, seconds_remaining, sigma)
```

¿Por qué este modelo es el núcleo?

Porque el contrato de Polymarket es binario. No necesitas predecir el precio exacto de BTC; necesitas estimar si termina arriba o abajo del strike.

---

# Modelo 3 — Z-score dinámico contra el strike

El Z-score mide distancia ajustada por riesgo:

```text
z = (S_t - K) / (S_t σ√τ)
```

En código:

```python
z_score_to_strike(price, strike, seconds_remaining, sigma)
```

Interpretación:

| Z-score | Lectura |
|---:|---|
| `0.10` | Ventaja débil |
| `0.50` | Ventaja moderada |
| `1.00` | Ventaja fuerte |
| `2.00` | Muy difícil que revierta |
| `-1.00` | Ventaja fuerte para DOWN |

¿Por qué va aquí?

Porque `S_t - K` solo en dólares engaña. Un movimiento de `$30` puede ser grande si faltan 10 segundos y la volatilidad está baja, pero puede ser pequeño si faltan 3 minutos y BTC está violento.

---

# Modelo 4 — Kalman Filter

Archivo:

```text
src/btc5m/models.py
```

Clase:

```python
KalmanPriceVelocity
```

Estado interno:

```text
x_t = [precio, velocidad]
```

Modelo conceptual:

```text
precio_real_t = precio_real_{t-1} + velocidad * Δt + ruido
precio_observado_t = precio_real_t + error
```

¿Por qué se usa?

Coinbase puede mandar ticks con ruido o retraso. El Kalman filter no elimina la latencia real, pero ayuda a:

- suavizar ticks raros,
- estimar velocidad corta,
- evitar que una sola lectura mueva demasiado la señal,
- generar `clean_price` para los modelos.

En el motor:

```text
raw Coinbase price → Kalman → clean_price
```

Ese `clean_price` alimenta:

- Brownian probability,
- Z-score,
- First-passage,
- Expected value.

---

# Modelo 5 — First-Passage / Reversal Probability

Cuando ya vas ganando, no basta con saber que BTC está arriba de `K`. También importa la probabilidad de que cruce de vuelta antes del cierre.

Aproximación por principio de reflexión en log-precio:

```text
P(hit K before T) ≈ 2 [1 - Φ(|ln(S_t / K)| / (σ√τ))]
```

En código:

```python
first_passage_probability_cross_strike(price, strike, seconds_remaining, sigma)
```

¿Por qué importa?

Ejemplo:

```text
compraste UP a 0.50
ahora UP vale 0.80
faltan 3 minutos
```

La pregunta ya no es solo si vas ganando. La pregunta es:

```text
¿qué probabilidad hay de que BTC vuelva a cruzar K antes del cierre?
```

Si esa probabilidad es alta, el motor puede sugerir `SELL_PARTIAL` o `SELL` aunque la posición vaya en ganancia.

---

# Modelo 6 — Expected Value vs precio de Polymarket

Para comprar UP:

```text
EV_buy_UP = p_UP - ask_UP
```

Para comprar DOWN:

```text
EV_buy_DOWN = p_DOWN - ask_DOWN
```

Donde:

```text
p_DOWN = 1 - p_UP
```

En código:

```python
expected_value_buy(prob_win, ask_price)
```

Regla inicial:

```text
si edge > min_edge_entry → posible entrada
```

Ejemplo:

```text
p_UP = 0.58
ask_UP = 0.53
edge_UP = 0.05
```

Hay edge teórico de `5 centavos` por contrato, antes de spread, slippage, fees y error del modelo.

¿Por qué se compara con `ask`?

Porque `ask` es el precio real al que puedes comprar ahora. El `mid` puede verse bonito, pero si nadie te vende a `mid`, no es tu costo de entrada.

---

# Modelo 7 — Expected Value Hold vs Sell

Cuando ya tienes posición, el precio de entrada es costo hundido para la decisión actual. La pregunta correcta es:

```text
¿mantener hasta cierre vale más que vender ahora?
```

Si tienes UP:

```text
EV_hold_UP = p_UP
EV_sell_UP = bid_UP
edge_hold = p_UP - bid_UP
```

En código:

```python
expected_value_hold(prob_win, current_bid)
```

Regla inicial:

```text
si edge_hold < min_hold_edge → SELL
```

Ejemplo:

```text
compraste a 0.50
bid actual = 0.80
p_UP modelo = 0.76
edge_hold = 0.76 - 0.80 = -0.04
```

Aunque vayas ganando, matemáticamente vender domina porque el mercado te paga `0.80` por algo que tu modelo valora en `0.76`.

---

# Modelo 8 — Optimal Stopping

Este modelo no es una fórmula única, sino una regla de decisión dinámica:

```text
V(estado) = max(vender ahora, mantener)
```

En el motor:

```text
sell_value = current_bid
hold_value = p_win
edge_hold = hold_value - sell_value
```

Variables del estado:

| Variable | Por qué importa |
|---|---|
| `p_win` | Valor esperado de mantener |
| `current_bid` | Valor seguro de salir ahora |
| `seconds_remaining` | Más tiempo = más riesgo de reversión |
| `reversal_probability` | Riesgo de cruzar el strike otra vez |
| `spread` | Costo real de entrar/salir |
| `latency_ms` | Riesgo de decidir con datos viejos |
| `position.side` | UP y DOWN usan probabilidades opuestas |

Acciones:

```text
WAIT
BUY_UP
BUY_DOWN
HOLD
SELL
SELL_PARTIAL
```

---

# Modelo 9 — Kelly fraccional

Kelly no predice dirección. Solo sugiere tamaño de posición cuando ya hay edge.

Para un contrato binario comprado a precio `q`:

```text
f* = (p - q) / (1 - q)
```

En código:

```python
kelly_fraction_binary(prob_win, entry_price)
```

Uso recomendado:

```text
Kelly bruto → demasiado agresivo
1/4 Kelly o 1/10 Kelly → más razonable
```

El motor solo imprime Kelly bruto como referencia. No ejecuta tamaño de posición.

---

## 7. Cómo se conectan los modelos entre sí

Flujo principal:

```text
1. Coinbase manda precio BTC.
2. Se calcula latencia y edad del dato.
3. EWMA actualiza volatilidad.
4. Kalman estima clean_price y velocidad.
5. Polymarket page da strike K y segundos restantes τ.
6. Brownian calcula p_UP_base.
7. Z-score mide distancia relativa a K.
8. Order book ajusta ligeramente probabilidad si hay presión de mercado.
9. Latencia reduce confianza si el dato está viejo.
10. Se obtiene p_UP_final.
11. Se compara p_UP_final contra ask_UP y ask_DOWN.
12. Si hay posición abierta, se compara hold vs sell.
```

---

## 8. Por qué no usar solo Optional Stopping Theorem

El Optional Stopping Theorem sirve como marco teórico para recordar que, si BTC fuera una martingala perfecta y el mercado fuera eficiente, una regla de parar no debería crear edge por sí sola.

Pero tu problema práctico es otro:

```text
estimar probabilidad terminal + comparar contra precio de mercado + decidir salida
```

Por eso el proyecto usa:

```text
Brownian probability + EWMA volatility + EV + Optimal Stopping
```

Y deja Optional Stopping como herramienta de validación conceptual, no como motor principal.

---

## 9. Machine Learning: cómo aprender pesos

El motor trae pesos manuales conservadores para momentum y order book:

```python
momentum_logit_weight = 0.35
orderbook_logit_weight = 0.20
```

Esto es solo un punto de partida. Lo correcto es guardar datos y entrenar.

Dataset recomendado:

```text
timestamp
round_slug
seconds_remaining
clean_price
strike_price
distance_to_strike
z_score
sigma_per_sqrt_second
p_up_base
p_up_final
reversal_probability
up_bid
up_ask
down_bid
down_ask
spread_up
spread_down
data_age_ms
exchange_latency_ms
result_up
```

Label:

```text
result_up = 1 si UP ganó
result_up = 0 si DOWN ganó
```

Entrenamiento base:

```powershell
python -m btc5m.ml_train_logistic --input data/features_labeled.csv --output models/logistic_calibrated.joblib
```

¿Por qué regresión logística primero?

- Es interpretable.
- Da probabilidades.
- Puedes ver pesos.
- Requiere menos datos que una red neuronal.
- Es buena línea base para comparar modelos más complejos.

Después puedes probar:

```text
Gradient Boosting / XGBoost / LightGBM
```

Redes neuronales solo después de tener mucho historial y un backtest correcto.

---

## 10. Validación correcta

No uses `random split` para validar, porque en trading eso mezcla pasado y futuro.

Mejor:

```text
entrenar con lunes-martes
probar miércoles

entrenar con lunes-miércoles
probar jueves

entrenar con lunes-jueves
probar viernes
```

Esto se llama `walk-forward validation`.

Métricas importantes:

| Métrica | Uso |
|---|---|
| `Brier Score` | Calidad de probabilidades |
| `Log Loss` | Penaliza probabilidades muy confiadas y equivocadas |
| `Calibration Curve` | Ver si 70% realmente gana ~70% |
| `PnL simulado` | Resultado con spread, slippage y latencia |
| `Max drawdown` | Riesgo de la estrategia |

No basta con `accuracy`.

---

## 11. Errores comunes que este diseño intenta evitar

### Error 1: ordenar por tiempo de llegada

Incorrecto:

```text
usar received_at como si fuera el tiempo real del precio
```

Correcto:

```text
usar exchange_time para el precio
usar received_at solo para medir latencia
```

---

### Error 2: usar la interfaz como fuente del bot

Incorrecto:

```text
Dashboard calcula → bot opera con eso
```

Correcto:

```text
Feeds → modelos → estado compartido → dashboard y bot leen lo mismo
```

---

### Error 3: mirar solo ganancia no realizada

Incorrecto:

```text
compré a 0.50, ahora vale 0.80, entonces aguanto
```

Correcto:

```text
si p_win < bid_actual, vender puede ser mejor
```

---

### Error 4: comparar probabilidad contra mid

Incorrecto:

```text
edge = p_modelo - mid
```

Correcto para entrada:

```text
edge = p_modelo - ask
```

Correcto para salida:

```text
edge_hold = p_modelo - bid
```

---

## 12. Cómo continuar el proyecto

Prioridad recomendada:

```text
1. Confirmar que Coinbase, Polymarket page y CLOB llegan al estado compartido.
2. Verificar que strike K y seconds_remaining sean correctos.
3. Guardar snapshots cada 200 ms en CSV.
4. Etiquetar cada ronda con result_up.
5. Backtestear Brownian + EWMA + EV.
6. Agregar Logistic Regression calibrada.
7. Comparar contra Polymarket sin copiar ciegamente su precio.
8. Después pensar en red neuronal o modelos secuenciales.
```

---

## 13. Nota sobre ejecución real

Antes de conectar cualquier bot que compre/venda, simula con:

```text
spread real
slippage
latencia
fallos de feed
mercados con poca liquidez
cierres de ronda
cambios de slug
```

El edge de un mercado de 5 minutos puede desaparecer por costos de ejecución o por datos atrasados.
