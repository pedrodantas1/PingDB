import sys
import os
import time
import subprocess
import logging
import traceback
import threading
from tkinter import Tk, Label, Button, Frame
from tkinter import font as tkFont

# --- CONFIGURAÇÕES GERAIS ---
IS_FROZEN = getattr(sys, 'frozen', False)
BASE_PATH = os.path.dirname(sys.executable if IS_FROZEN else __file__)

# --- CORREÇÃO CRÍTICA PARA O .EXE ---
# Força o diretório de trabalho a ser o mesmo do executável
if IS_FROZEN:
    os.chdir(BASE_PATH)

# Arquivos de controle e logs
LOCK_FILE = os.path.join(BASE_PATH, '.pingdb.lock')
LOG_FILE = os.path.join(BASE_PATH, 'ping-service.log')
GUI_LOG_FILE = os.path.join(BASE_PATH, 'gui-errors.log')

# Configuração do Logger para o serviço de fundo
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

# Configurações de Conexão com o Banco
CONN_STR = (
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=localhost;'
    r'DATABASE=Etrade;'
    r'Trusted_Connection=yes;'
)
PING_INTERVALO_SEGUNDOS = 10

# --- LÓGICA DO SERVIÇO DE PING (BACKGROUND) ---
def run_ping_loop():
    logging.info("Serviço de background iniciado.")
    while True:
        if not os.path.exists(LOCK_FILE):
            logging.info("Arquivo de lock não encontrado. Encerrando o serviço de background.")
            break
        
        conn = None
        try:
            import pyodbc # Importa aqui para garantir que esteja no escopo do processo filho
            conn = pyodbc.connect(CONN_STR, timeout=5)
            cursor = conn.cursor()
            start_time = time.time()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            tempo_ms = (time.time() - start_time) * 1000
            logging.info(f"Ping realizado com sucesso ({tempo_ms:.2f} ms).")
        except Exception as ex:
            logging.error(f"Erro no ping ou conexão: {ex}")
            logging.error(traceback.format_exc())
        finally:
            if conn:
                conn.close()
        time.sleep(PING_INTERVALO_SEGUNDOS)

# --- FUNÇÕES DE CONTROLE (START, STOP, STATUS) ---
def get_running_pid():
    if not os.path.exists(LOCK_FILE):
        return None
    try:
        with open(LOCK_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}'],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        if str(pid) in result.stdout:
            return pid
        else:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
            return None
    except (IOError, ValueError):
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        return None

def start_service():
    if get_running_pid():
        return
    try:
        if IS_FROZEN:
            command = [sys.executable, '--background']
        else:
            command = [sys.executable, __file__, '--background']

        subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
        logging.info(f"Comando para iniciar serviço executado: {' '.join(command)}")

    except Exception as e:
        logging.error(f"Falha ao iniciar o subprocesso: {e}")
        traceback.print_exc()


def stop_service():
    pid = get_running_pid()
    if not pid:
        return
    try:
        subprocess.run(
            ['taskkill', '/PID', str(pid), '/F'],
            check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
    except subprocess.CalledProcessError:
        pass
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

# --- INTERFACE GRÁFICA (GUI) com TKINTER ---
class AppGUI(Tk):
    def __init__(self):
        super().__init__()
        self.title("PingDB Control")
        self.geometry("400x300")
        self.resizable(False, False)
        self.configure(bg="#F0F0F0")

        self.center_window()
        self.create_widgets()
        self.update_status()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        main_font = tkFont.Font(family="Segoe UI", size=10)
        title_font = tkFont.Font(family="Segoe UI", size=14, weight="bold")

        container = Frame(self, bg="#FFFFFF", bd=1, relief="solid", padx=20, pady=20)
        container.pack(expand=True, fill="both", padx=20, pady=20)

        Label(container, text="🚀 Controle PingDB", font=title_font, bg="#FFFFFF", fg="#005A9E").pack(pady=(0, 20))

        status_frame = Frame(container, bd=1, relief="solid", bg="#E0E0E0")
        status_frame.pack(fill="x", pady=10, ipady=10)
        
        Label(status_frame, text="Status do Serviço:", font=main_font, bg="#E0E0E0").pack(side="left", padx=10)
        self.status_label = Label(status_frame, text="Verificando...", font=tkFont.Font(family="Segoe UI", size=10, weight="bold"), bg="#E0E0E0")
        self.status_label.pack(side="left")

        self.btn_start = Button(container, text="Iniciar Ping", command=self.on_start, font=main_font, bg="#28a745", fg="white", relief="flat", width=15, pady=5)
        self.btn_start.pack(pady=5)

        self.btn_stop = Button(container, text="Parar Ping", command=self.on_stop, font=main_font, bg="#dc3545", fg="white", relief="flat", width=15, pady=5)
        self.btn_stop.pack(pady=5)
        
        Label(container, text="Pode fechar esta janela a qualquer momento.", font=tkFont.Font(family="Segoe UI", size=8), bg="#FFFFFF", fg="#666").pack(pady=(20, 0))

    def update_status(self):
        if get_running_pid():
            self.status_label.config(text="Executando", fg="#006400")
            self.btn_start.config(state="disabled", bg="#a9a9a9")
            self.btn_stop.config(state="normal", bg="#dc3545")
        else:
            self.status_label.config(text="Parado", fg="#A80000")
            self.btn_start.config(state="normal", bg="#28a745")
            self.btn_stop.config(state="disabled", bg="#a9a9a9")
        
        self.after(2000, self.update_status)

    def on_start(self):
        start_service()

    def on_stop(self):
        stop_service()

# --- PONTO DE ENTRADA PRINCIPAL ---
def main():
    # Esta verificação garante que a GUI só rode no processo principal
    if '--background' in sys.argv:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        run_ping_loop()
    else:
        try:
            app = AppGUI()
            app.mainloop()
        except Exception as e:
            with open(GUI_LOG_FILE, 'a') as f:
                f.write(f"Ocorreu um erro na GUI em {time.ctime()}:\n")
                f.write(traceback.format_exc())
                f.write("\n")

if __name__ == '__main__':
    main()

