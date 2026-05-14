import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from influxdb_client import InfluxDBClient
from datetime import datetime
import time

# --- CONFIGURACIÓN DE INFLUXDB ---
url = "[https://us-east-1-1.aws.cloud2.influxdata.com](https://us-east-1-1.aws.cloud2.influxdata.com/)"   # Cambia por la URL de tu servidor Influx
token = "JoKdx3OFaBCFPmYQgiVWE8hjrtJ0lDkjwWZzT9djWJlvg98rtTgF9iRgKhQtAkKIA2UQsU6zsrJlv1BH6lfsVw=="              # Token de autenticación
org = "miguelcmo "                  # Organización
bucket = "iot_telemetry_data"            # Bucket donde están los datos

client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

st.title("Dashboard IoT con DHT22 y MPU6050")

# --- FILTROS ---
device_id = st.text_input("Filtrar por device_id (opcional)")
fecha_inicio = st.date_input("Fecha inicial")
fecha_fin = st.date_input("Fecha final")

# --- FUNCIÓN PARA CONSULTAR DATOS ---
def get_data():
    # Convertir fechas a RFC3339
    start_str = datetime.combine(fecha_inicio, datetime.min.time()).isoformat() + "Z"
    end_str = datetime.combine(fecha_fin, datetime.max.time()).isoformat() + "Z"

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {start_str}, stop: {end_str})
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
    return pd.DataFrame(records)

# --- LOOP DE ACTUALIZACIÓN CADA 5 MIN ---
while True:
    df = get_data()

    if not df.empty:
        st.write("Vista previa de los datos:", df.head())

        # --- ESTADÍSTICAS ---
        temp_mean = df[df["field"]=="temperature"]["value"].mean()
        hum_mean = df[df["field"]=="humidity"]["value"].mean()
        accel_x_max = df[df["field"]=="accel_x"]["value"].max()
        accel_y_max = df[df["field"]=="accel_y"]["value"].max()
        accel_z_max = df[df["field"]=="accel_z"]["value"].max()

        st.write("Temperatura promedio (DHT22):", round(temp_mean, 2))
        st.write("Humedad promedio (DHT22):", round(hum_mean, 2))
        st.write("Máxima aceleración X (MPU6050):", accel_x_max)
        st.write("Máxima aceleración Y (MPU6050):", accel_y_max)
        st.write("Máxima aceleración Z (MPU6050):", accel_z_max)

        # --- GRÁFICAS ---
        st.subheader("Gráficas")

        # Serie de tiempo: temperatura
        temp_df = df[df["field"]=="temperature"]
        fig, ax = plt.subplots()
        ax.plot(temp_df["timestamp"], temp_df["value"], color="red")
        ax.set_title("Temperatura vs Tiempo (DHT22)")
        st.pyplot(fig)

        # Serie de tiempo: humedad
        hum_df = df[df["field"]=="humidity"]
        fig, ax = plt.subplots()
        ax.plot(hum_df["timestamp"], hum_df["value"], color="blue")
        ax.set_title("Humedad vs Tiempo (DHT22)")
        st.pyplot(fig)

        # Serie de tiempo: aceleraciones
        for axis in ["accel_x", "accel_y", "accel_z"]:
            accel_df = df[df["field"]==axis]
            fig, ax = plt.subplots()
            ax.plot(accel_df["timestamp"], accel_df["value"])
            ax.set_title(f"Aceleración {axis.upper()} vs Tiempo (MPU6050)")
            st.pyplot(fig)

        # --- INTERPRETACIONES DINÁMICAS ---
        st.subheader("Interpretaciones")
        if temp_mean > 30:
            st.warning("Advertencia: La temperatura promedio supera los 30°C.")
        if hum_mean < 30:
            st.warning("Advertencia: Humedad baja detectada.")
        if accel_x_max > 2 or accel_y_max > 2 or accel_z_max > 2:
            st.error("Alerta: Movimiento brusco detectado en el MPU6050.")

    # Espera 5 minutos antes de actualizar
    time.sleep(300)

