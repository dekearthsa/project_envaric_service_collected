import time
import requests
import schedule
from bs4 import BeautifulSoup
import pandas as pd
import mysql.connector
from datetime import datetime
import os 

### URL production
URL = "http://192.168.10.1/LastLog.cgi?lognum=61"

# ### URL demo docker env
# URL = "http://localhost:9001/LastLog.cgi"

DB_CONFIG = {
    "host": "localhost",  
    "user": "root",
    "password": "rootpassword",
    "database": "mydatabase",
    "port": 3306  
}

def insert_csv_file(df):
    now = datetime.now()
    path_time_stamp = now.strftime("%d_%m_%y")
    output_path=f"./csv/{path_time_stamp}/data.csv"
    date_file = f"./csv/{path_time_stamp}"
    filepath_by_date = os.path.join(os.getcwd(), date_file)
    check_file_path = os.path.isdir(filepath_by_date)
    
    if check_file_path == False:
        os.mkdir(date_file)
        df_existing = pd.DataFrame() 
        df_combined = pd.concat([df_existing, df], ignore_index=True)
        df_combined = df_combined.drop_duplicates()
        df_combined.to_csv(output_path, index=False)
    else:
        try:
            df_existing = pd.read_csv(output_path)
        except FileNotFoundError:
            df_existing = pd.DataFrame() 
        df_combined = pd.concat([df_existing, df], ignore_index=True)
        df_combined = df_combined.drop_duplicates()
        df_combined.to_csv(output_path, index=False)

def insert_data(df):
    print("start insert....")
    try:
        print("conn = mysql.connector.connect(**DB_CONFIG)")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        # print(df)
        # print(df['VOC'])
        insert_query = "INSERT INTO airQuality (strDatetime, ms, VOC, CO2, CH2O, eVOC, Humid, Temp, `PM2.5`, `PM10`, CO) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        print("cursor.execute(insert_query, values)")
        for _, row in df.iterrows():
            # print("row =>", row['strDatetime'], type(row['strDatetime']))
            # print("row =>", row['ms'] , type(row['ms']))
            # print("row =>", row['VOC(ppb)'] , type(row['VOC(ppb)']))
            # print("row =>", row['CO2(ppm)'] , type(row['CO2(ppm)']))
            # print("row =>", row['CH2O(ppm)'], type(row['CH2O(ppm)']))
            # print("row =>", row['eVOC(ppb)'], type(row['eVOC(ppb)']))
            # print("row =>", row['Humid(%)'], type(row['Humid(%)']))
            # print("row =>", row['Temp(C)'], type(row['Temp(C)']))
            # print("row =>", row['PM2.5(ug/m3)'], type(row['PM2.5(ug/m3)']))
            # print("row =>", row['PM10(ug/m3)'], type(row['PM10(ug/m3)']))
            # print("row =>", row['CO(ppm)'], type(row['CO(ppm)']))
            values = (
                # row['Date Time'], 
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
            print("Executing insert with values:", values)  
            cursor.execute(insert_query, values)
        conn.commit()
        print("Data inserted successfully!")
    except mysql.connector.Error as e:
        print(f"Database Insert Error: {e}")
    finally:
        print("Closing connection...")
        cursor.close()
        conn.close()

def data_convert(table):
    headers = [th.text.strip() for th in table.find_all("tr")[0].find_all("td")]
    data = []
    for row in table.find_all("tr")[1:]:   
        cols = [td.text.strip() for td in row.find_all("td")]
        if len(cols) == len(headers):  
            data.append(cols)

    df = pd.DataFrame(data, columns=headers)
    string_data = df['Date Time']
    # print(string_data)
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
            return  int(dt_obj.timestamp() * 1000)
        except ValueError:
            return None 
    df['ms'] = df['strDatetime'].apply(parse_ms)
    df = df.drop(columns=['strDatetime'])
    
    for col in df.columns[1:]: 
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['strDatetime'] = string_data
    # insert_data(df)
    insert_csv_file(df)

def fetch_data():
    try:
        print("fetch_data")
        res = requests.get(URL, timeout=30)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find("table", style="text-align:center;width:100%;border:1px solid black;border-collapse: collapse;")
            # print(table)
            data_convert(table)
        else:
            print(f"Failed with status code {res.status_code}")
    except Exception as e:
        print(f"{e}")

## running for test demo ##
print("start....")
schedule.every(1).minutes.do(fetch_data)  

if __name__ == "__main__":
    print("Starting HTTP polling service...")
    while True:
        schedule.run_pending()
        time.sleep(1) 

