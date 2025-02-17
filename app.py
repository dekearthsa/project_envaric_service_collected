import time
import requests
import schedule
from bs4 import BeautifulSoup
import pandas as pd
import mysql.connector
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import os


URL = "http://192.168.10.1/LastLog.cgi?lognum=21"
TOPIC = "v1/devices/me/telemetry"
MQTT_HOST =  "mqtt.thingsboard.cloud"
MQTT_PORT = 1883
ACCESS_TOKEN = "7Mv5BGOOqQmLfN7xlZbU"

DB_CONFIG = {
    "host": "localhost",  
    "user": "root",
    "password": "rootpassword",
    "database": "mydatabase",
    "port": 3306  
}

client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)

def on_connect(client, userdata, flags, rc):

    if rc == 0:
        print("Connected to MQTT broker successfully.")
    else:
        print(f"Failed to connect. Error code = {rc}")

def on_disconnect(client, userdata, rc):

    if rc != 0:
        print("Unexpected disconnection. Reconnecting...")
        try:
            client.reconnect()
        except Exception as e:
            print(f"Reconnection error: {e}")
    else:
        print("Disconnected from MQTT broker.")


client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

def insert_csv_file(df):
    now = datetime.now()
    path_time_stamp = now.strftime("%d_%m_%y")
    output_path = f"./csv/{path_time_stamp}/data.csv"
    date_file = f"./csv/{path_time_stamp}"
    filepath_by_date = os.path.join(os.getcwd(), date_file)
    check_file_path = os.path.isdir(filepath_by_date)
    
    if not check_file_path:
        os.mkdir(date_file)
        df_existing = pd.DataFrame()
    else:
        try:
            df_existing = pd.read_csv(output_path)
        except FileNotFoundError:
            df_existing = pd.DataFrame()
    
    df_combined = pd.concat([df_existing, df], ignore_index=True).drop_duplicates()
    df_combined.to_csv(output_path, index=False)

def data_convert_to_dashboard(df):
    # print("Start sending data via MQTT...")
    data = []
    for _, row in df.iterrows():
        payload = {
            "ts": row['ms'],
            "values": {
                "VOC": row['VOC(ppb)'],
                "CO2": row['CO2(ppm)'],
                "CH2O": row['CH2O(ppm)'],
                "eVOC": row['eVOC(ppb)'],
                "Humid": row['Humid(%)'],
                "Temp": row['Temp(C)'],
                "PM2.5": row['PM2.5(ug/m3)'],
                "PM10": row['PM10(ug/m3)'],
                "CO": row['CO(ppm)']
            }
        }
        data.append(payload)
    payload_json = json.dumps(data)
    result = client.publish(TOPIC, payload_json)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"Published payload successfully: {payload_json}")
    else:
        print("Failed to publish MQTT message.")

def insert_data(df):
    # print("Start DB insert...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO airQuality 
            (strDatetime, ms, VOC, CO2, CH2O, eVOC, Humid, Temp, `PM2.5`, `PM10`, CO)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for _, row in df.iterrows():
            values = (
                str(row['strDatetime']),
                int(row['ms']),
                int(row['VOC(ppb)']), 
                int(row['CO2(ppm)']), 
                float(row['CH2O(ppm)']), 
                int(row['eVOC(ppb)']), 
                float(row['Humid(%)']), 
                float(row['Temp(C)']), 
                float(row['PM2.5(ug/m3)']), 
                float(row['PM10(ug/m3)']), 
                float(row['CO(ppm)'])
            )
            cursor.execute(insert_query, values)
        conn.commit()
        # print("Data inserted successfully!")

        data_convert_to_dashboard(df)
    except mysql.connector.Error as e:
        print(f"Database Insert Error: {e}")
    finally:
        cursor.close()
        conn.close()
        print("DB connection closed.")

def data_convert(table):
    headers = [th.text.strip() for th in table.find_all("tr")[0].find_all("td")]
    data = []
    for row in table.find_all("tr")[1:]:
        cols = [td.text.strip() for td in row.find_all("td")]
        if len(cols) == len(headers):
            data.append(cols)

    df = pd.DataFrame(data, columns=headers)
    string_data = df['Date Time']
    df["strDatetime"] = df['Date Time']

    def parse_datetime(dt_str):
        try:
            return datetime.strptime(dt_str, "%d/%m/%y %H:%M").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    df['Date Time'] = df['strDatetime'].apply(parse_datetime)

    def parse_ms(dt_str):
        try:
            dt_obj = datetime.strptime(dt_str, "%d/%m/%y %H:%M")
            return int(dt_obj.timestamp() * 1000)
        except ValueError:
            return None

    df['ms'] = df['strDatetime'].apply(parse_ms)
    df = df.drop(columns=['strDatetime'])
    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['strDatetime'] = string_data
    insert_data(df)
    # insert_csv_file(df)

def fetch_data():
    try:
        # print("Fetching data from:", URL)
        res = requests.get(URL, timeout=30)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find("table", style="text-align:center;width:100%;border:1px solid black;border-collapse: collapse;")
            if table:
                data_convert(table)
            else:
                print("No valid table found on page.")
        else:
            print(f"Failed to fetch data. Status code: {res.status_code}")
    except Exception as e:
        print(f"Exception in fetch_data: {e}")

fetch_data()
schedule.every(1).minutes.do(fetch_data)

if __name__ == "__main__":
    print("Starting HTTP polling + MQTT service...")
    while True:
        schedule.run_pending()
        time.sleep(1)
