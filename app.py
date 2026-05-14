import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from influxdb_client import InfluxDBClient
import time

# --- CONFIGURACIÓN DE INFLUXDB ---
url = "http://localhost:8086"   # Cambia por la URL de tu servidor Influx
token = "TU_TOKEN"              # Token de autenticación
org = "TU_ORG"                  # Organización
bucket = "TU_BUCKET"            # Bucket donde están los datos

client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

st.title("Dashboard IoT con InfluxDB")

# --- FILTROS ---
device_id = st.text_input("Filtrar por device_id (opcional)")
fecha_inicio = st.date_input("Fecha inicial")
fecha_fin = st.date_input("Fecha final")

# --- FUNCIÓN PARA CONSULTAR DATOS ---
def get_data():
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {fecha_inicio}, stop: {fecha_fin})
      |> filter(fn: (r) => r["_measurement"] == "iot_data")
    '''
    if device_id:
        query += f'  |> filter(fn: (r) => r["device_id"] == "{device_id}")'

    tables = query_api.query(query)
    records = []
    for table in tables:
        for record in table.records:
            records.append({
                "timestamp": record["_time"],
                "field": record["_field"],
                "value": record["_value"],
                "device_id": record["device_id"]
            })
    df = pd.DataFrame(records)
    return df

# --- LOOP DE ACTUALIZACIÓN CADA 5 MIN ---
while True:
    df = get_data()

    if not df.empty:
        st.write("Vista previa de los datos:", df.head())

        # Estadísticas
        temp_mean = df[df["field"]=="temperature"]["value"].mean()
        energy_mean = df[df["field"]=="energy_consumption"]["value"].mean()
        vibration_max = df[df["field"]=="vibration"]["value"].max()

        st.write("Temperatura promedio:", round(temp_mean, 2))
        st.write("Consumo energético promedio:", round(energy_mean, 2))
        st.write("Máxima vibración:", vibration_max)

        # Gráficas
        st.subheader("Gráficas")

        # Serie de tiempo: temperatura vs tiempo
        temp_df = df[df["field"]=="temperature"]
        fig, ax = plt.subplots()
        ax.plot(temp_df["timestamp"], temp_df["value"])
        ax.set_title("Temperatura vs Tiempo")
        st.pyplot(fig)

        # Histograma de consumo energético
        energy_df = df[df["field"]=="energy_consumption"]
        fig, ax = plt.subplots()
        ax.hist(energy_df["value"], bins=30, color="skyblue", edgecolor="black")
        ax.set_title("Distribución de Consumo Energético")
        st.pyplot(fig)

        # Relación entre variables: temperatura vs consumo energético
        merged = pd.merge(temp_df, energy_df, on="timestamp", suffixes=("_temp","_energy"))
        fig, ax = plt.subplots()
        ax.scatter(merged["value_temp"], merged["value_energy"], alpha=0.5)
        ax.set_title("Temperatura vs Consumo Energético")
        st.pyplot(fig)

        # Interpretaciones dinámicas
        st.subheader("Interpretaciones")
        if temp_mean > 30:
            st.warning("Advertencia: La temperatura promedio supera los 30°C.")
        if vibration_max > 50:
            st.error("Alerta: Vibración crítica detectada.")

    # Espera 5 minutos antes de actualizar
    time.sleep(300)
