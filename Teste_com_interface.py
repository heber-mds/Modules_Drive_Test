import serial
import pynmea2
import numpy as np
from scipy.interpolate import interp1d
import time
from datetime import datetime
from database import collection
import tkinter as tk
from tkinter import ttk


def calcular_media_coordenadas_satelites(dados_gpgsv):
    coordenadas_satelites = []
    for linha in dados_gpgsv:
        mensagem = pynmea2.parse(linha)
        if isinstance(mensagem, pynmea2.GSV) and int(mensagem.num_sv_in_view) > 0:
            for i in range(1, 5):
                if getattr(mensagem, f'sv_prn_num_{i}') != '':
                    lat = float(getattr(mensagem, f'sv_prn_num_{i}', 0.0)) / 100.0
                    lon = float(getattr(mensagem, f'sv_prn_num_{i}', 0.0)) / 100.0
                    coordenadas_satelites.append((lat, lon))
    
    if not coordenadas_satelites:
        return None, None
    
    latitudes = [coord[0] for coord in coordenadas_satelites]
    longitudes = [coord[1] for coord in coordenadas_satelites]
    
    return np.mean(latitudes), np.mean(longitudes)


def extrair_coordenadas(mensagem):
    latitude = float(mensagem.lat[:2]) + float(mensagem.lat[2:]) / 60
    if mensagem.lat_dir == 'S':
        latitude = -latitude
    longitude = float(mensagem.lon[:3]) + float(mensagem.lon[3:]) / 60
    if mensagem.lon_dir == 'W':
        longitude = -longitude
    return latitude, longitude


def obter_intensidade_sinal(ser_signal):
    ser_signal.write(b'AT+QCSQ\r')
    time.sleep(0.5)
    lines = ser_signal.readlines()
    for line in lines:
        line = line.decode('ascii', errors='replace').strip()
        if line.startswith('+QCSQ'):
            print(f"Signal Strength Message: {line}")
            parts = line.split(',')
            signal_strength = int(parts[1])
            print(f"Signal Strength in dB: {signal_strength}")
            return signal_strength
    return None


def iniciar_leitura():
    global running
    running = True
    ser_gps_port = gps_port_entry.get()
    ser_gps_baud = int(gps_baud_entry.get())
    ser_signal_port = signal_port_entry.get()
    ser_signal_baud = int(signal_baud_entry.get())
    record_name = record_entry.get()

    # Configuração das portas seriais
    ser_gps = serial.Serial(ser_gps_port, ser_gps_baud, timeout=1)
    ser_signal = serial.Serial(ser_signal_port, ser_signal_baud, timeout=1)

    latitude = 0
    longitude = 0
    coordinates = []

    while running:
        start_time = time.time()
        while time.time() - start_time < 3 and running:
            line = ser_gps.readline().decode('ascii', errors='replace').strip()
            
            if not line:
                continue

            if line.startswith('$GPRMC'):
                msg = pynmea2.parse(line)
                latitude, longitude = extrair_coordenadas(msg)
                coordinates.append([latitude, longitude])
                print(f"Latitude GPS: {latitude}")
                print(f"Longitude GPS: {longitude}")

            elif line.startswith('$GPGGA'):
                msg = pynmea2.parse(line)
                latitude, longitude = extrair_coordenadas(msg)
                coordinates.append([latitude, longitude])
                print(f"Latitude GPS: {latitude}")
                print(f"Longitude GPS: {longitude}")

        # Interpolação das coordenadas
        latitudes = [coord[0] for coord in coordinates]
        longitudes = [coord[1] for coord in coordinates]

        if len(latitudes) > 1 and len(longitudes) > 1:
            interpolated_latitudes = interp1d(np.arange(len(latitudes)), latitudes, kind="linear")(np.arange(0, len(latitudes), 5))
            interpolated_longitudes = interp1d(np.arange(len(longitudes)), longitudes, kind="linear")(np.arange(0, len(longitudes), 5))
            
            # Obter intensidade do sinal
            received_signal_strength_indication = obter_intensidade_sinal(ser_signal)
            
            documents = [] 
            for interpolated_latitude, interpolated_longitude in zip(interpolated_latitudes, interpolated_longitudes):
                print(f"Interpolated Latitude: {interpolated_latitude}")
                print(f"Interpolated Longitude: {interpolated_longitude}")
                documents.append({
                    "timestamp": datetime.now(),
                    "latitude": interpolated_latitude,
                    "longitude": interpolated_longitude,
                    "received_signal_strength_indication": received_signal_strength_indication,
                    "record": record_name,
                })

            collection.insert_many(documents=documents)
        else:
            print("Not enough data for interpolation")


def pausar_leitura():
    global running
    running = False


# Interface Gráfica
root = tk.Tk()
root.title("Configuração do Teste")

# Nome do Teste
ttk.Label(root, text="Nome do Teste:").grid(row=0, column=0, padx=10, pady=10)
record_entry = ttk.Entry(root)
record_entry.grid(row=0, column=1, padx=10, pady=10)

# Configuração GPS
ttk.Label(root, text="Porta GPS:").grid(row=1, column=0, padx=10, pady=10)
gps_port_entry = ttk.Entry(root)
gps_port_entry.grid(row=1, column=1, padx=10, pady=10)
ttk.Label(root, text="Baud Rate GPS:").grid(row=2, column=0, padx=10, pady=10)
gps_baud_entry = ttk.Entry(root)
gps_baud_entry.grid(row=2, column=1, padx=10, pady=10)

# Configuração do Sinal
ttk.Label(root, text="Porta Sinal:").grid(row=3, column=0, padx=10, pady=10)
signal_port_entry = ttk.Entry(root)
signal_port_entry.grid(row=3, column=1, padx=10, pady=10)
ttk.Label(root, text="Baud Rate Sinal:").grid(row=4, column=0, padx=10, pady=10)
signal_baud_entry = ttk.Entry(root)
signal_baud_entry.grid(row=4, column=1, padx=10, pady=10)

# Botões Play e Pause
play_button = ttk.Button(root, text="Iniciar Leitura", command=iniciar_leitura)
play_button.grid(row=5, column=0, padx=10, pady=20)

pause_button = ttk.Button(root, text="Pausar Leitura", command=pausar_leitura)
pause_button.grid(row=5, column=1, padx=10, pady=20)

root.mainloop()
