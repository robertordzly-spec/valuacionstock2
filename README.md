# Indicadores de Valuación de Activos — App de Streamlit

App construida a partir de:
- `instrucciones codigo phyton.docx` (inputs, indicadores y formato requeridos)
- `E7 RD4 Metricas valuacion de activos.pdf` (definición conceptual de cada indicador)
- `E7 RD3 Modelo de valuacion de activos.xlsx` (fórmulas exactas replicadas en el código)

## Qué calcula

Para cada activo, contra el índice bursátil de referencia seleccionado:

- Rentabilidad anualizada y volatilidad anualizada
- Índice Sharpe
- Coeficiente de correlación de Pearson vs el índice
- Beta (pendiente de la regresión activo vs índice)
- Índice Treynor
- CAPM y Alpha (Jensen)
- Intervalo de confianza, nivel de significancia y valor "z"
- VaR en $ y en % (método paramétrico varianza-covarianza)
- Gráfica de dispersión + regresión lineal (con la fórmula y R² en la propia gráfica)

Datos: precios de cierre ajustado de Yahoo Finance vía `yfinance`.

## Correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Subir a GitHub y desplegar en Streamlit Community Cloud

1. Crea un repositorio nuevo en GitHub y sube `app.py`, `requirements.txt` y este `README.md`.
2. Entra a https://share.streamlit.io/ , conecta tu cuenta de GitHub y selecciona el repo.
3. Define `app.py` como archivo principal y despliega.

## Notas

- La tasa libre de riesgo se introduce manualmente (por defecto 4.57%, referencia del bono
  del Tesoro de EE. UU. a 10 años); ajústala según el país de origen de los activos que valúes.
- "Plazo para VaR" = 1 día usa la volatilidad diaria tal cual; "1 mes" escala por √21
  (días hábiles aproximados en un mes).
- Todas las fórmulas replican celda por celda la hoja "Métricas" del archivo Excel de referencia.
