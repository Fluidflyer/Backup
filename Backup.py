import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime
import threading
import ctypes
import sys

# Überprüfen, ob das Skript mit Administratorrechten läuft
if not ctypes.windll.shell32.IsUserAnAdmin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, ' '.join(sys.argv), None, 1)
    sys.exit()


# Globale Variablen
source_drive = ""
target_drive = ""
total_files = 0
files_processed = 0
backup_running = False  # Globale Variable für den Backup-Status

# Liste von zu ignorierenden Systemdateien
system_files_to_ignore = ["bootmgr", "pagefile.sys", "hiberfil.sys"]

# Funktion, um das ausgewählte Quell- und Ziel-Laufwerk festzulegen
def set_source_drive():
    global source_drive
    source_drive = filedialog.askdirectory(title="Wählen Sie das Quell-Laufwerk aus")
    source_label.config(text=f"Quelle: {source_drive}")

def set_target_drive():
    global target_drive
    target_drive = filedialog.askdirectory(title="Wählen Sie das Ziel-Laufwerk aus")
    target_label.config(text=f"Ziel: {target_drive}")

# Funktion zum Starten des Backups im Hintergrund
def perform_backup_thread():
    global backup_running
    if not backup_running:
        backup_running = True
        threading.Thread(target=perform_backup, daemon=True).start()  # Der Thread wird als "Daemon" gestartet.
    else:
        messagebox.showwarning("Backup läuft bereits", "Es läuft bereits ein Backup-Prozess.")

# Funktion für die Durchführung des Backups
def perform_backup():
    global files_processed, total_files, backup_running
    if not source_drive or not target_drive:
        messagebox.showwarning("Fehler", "Bitte wählen Sie sowohl Quelle als auch Ziel aus.")
        return

    try:
        # Sicherstellen, dass der Zielordner existiert, andernfalls erstellen
        if not os.path.exists(target_drive):
            os.makedirs(target_drive)

        # Berechnen der Gesamtzahl an Dateien
        total_files = sum([len(files) for _, _, files in os.walk(source_drive)])
        files_processed = 0

        # Fortschrittsanzeige für das Backup
        progress_bar["maximum"] = total_files
        progress_bar["value"] = 0
        percentage_label.config(text="0%")

        # Kopieren aller Dateien und Ordner
        for root, dirs, files in os.walk(source_drive):
            if not backup_running:  # Überprüfen, ob das Backup gestoppt wurde
                break

            relative_path = os.path.relpath(root, source_drive)
            target_dir = os.path.join(target_drive, relative_path)

            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            for file in files:
                if not backup_running:  # Überprüfen, ob das Backup gestoppt wurde
                    break
                if file.lower() in system_files_to_ignore:
                    continue

                source_file = os.path.join(root, file)
                target_file = os.path.join(target_dir, file)

                # Prüfen, ob die Datei lesbar ist, bevor sie kopiert wird
                if not os.access(source_file, os.R_OK):
                    log_backup(f"Zugriffsfehler: {source_file} kann nicht gelesen werden.")
                    continue  # Datei überspringen, wenn sie nicht zugänglich ist

                try:
                    shutil.copy2(source_file, target_file)  # Kopieren und Metadaten beibehalten
                    files_processed += 1
                    progress_bar["value"] = files_processed
                    percentage_label.config(text=f"{(files_processed / total_files) * 100:.2f}%")
                    root.update_idletasks()  # GUI-Update während des Kopierens
                except PermissionError as e:
                    log_backup(f"Zugriffsfehler: {str(e)} beim Kopieren der Datei {source_file}. Datei wird übersprungen.")
                    continue  # Datei überspringen, wenn Zugriff verweigert wird
                except OSError as e:
                    if e.errno == 5:  # WinError 5 - Zugriff verweigert
                        log_backup(f"WinError 5: Zugriff verweigert beim Kopieren der Datei {source_file}. Datei wird übersprungen.")
                    else:
                        log_backup(f"Fehler: {str(e)} beim Kopieren der Datei {source_file}.")
                    continue
                except Exception as e:
                    log_backup(f"Fehler beim Kopieren der Datei {source_file}: {str(e)}")
                    continue

        progress_bar["value"] = total_files
        percentage_label.config(text="100%")
        log_backup("Backup erfolgreich abgeschlossen!")
        messagebox.showinfo("Erfolg", "Das Backup wurde erfolgreich durchgeführt.")
    except PermissionError as e:
        log_backup(f"Zugriffsfehler beim Starten des Backups: {str(e)}")
        messagebox.showerror("Fehler", f"Zugriffsfehler: {str(e)}. Stellen Sie sicher, dass Sie Administratorrechte haben.")
    except Exception as e:
        log_backup(f"Fehler beim Backup: {str(e)}")
        messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {str(e)}")
    finally:
        backup_running = False

# Funktion zum Protokollieren des Backups
def log_backup(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open("backup_log.txt", "a", encoding="utf-8") as log_file:
            log_file.write(f"{timestamp} - {message}\n")
    except Exception as e:
        print(f"Fehler beim Schreiben der Logdatei: {e}")

# GUI erstellen
root = tk.Tk()
root.title("Automatisiertes Backup-Programm")

# Label für Quelle und Ziel
source_label = tk.Label(root, text="Quelle: (Noch nicht ausgewählt)", width=50, anchor="w")
source_label.pack(pady=10)
target_label = tk.Label(root, text="Ziel: (Noch nicht ausgewählt)", width=50, anchor="w")
target_label.pack(pady=10)

# Buttons zum Auswählen der Quelle und des Ziels
source_button = tk.Button(root, text="Quelle auswählen", command=set_source_drive)
source_button.pack(pady=5)
target_button = tk.Button(root, text="Ziel auswählen", command=set_target_drive)
target_button.pack(pady=5)

# Button zum sofortigen Durchführen eines Backups (im Hintergrund starten)
backup_button = tk.Button(root, text="Backup jetzt durchführen", command=perform_backup_thread)
backup_button.pack(pady=20)

# Fortschrittsanzeige (ProgressBar)
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")  # Hier wird ttk verwendet
progress_bar.pack(pady=10)

# Prozentanzeige für den Fortschritt
percentage_label = tk.Label(root, text="0%", width=10, anchor="w")
percentage_label.pack(pady=5)

# Starten der GUI-Schleife
root.mainloop()
