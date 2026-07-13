import sqlite3, os, numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest

# Identifica o diretório privado do aplicativo Android. Se não estiver no Android, usa a pasta local.
BASE_DIR = os.environ.get('ANDROID_PRIVATE_DATA', os.path.dirname(os.path.abspath(__file__)))
CAMINHO_DB = os.path.join(BASE_DIR, "guardiao.db")

class AprendizRotina:
    def __init__(self):
        self.dias_treinados = 0
        self.dias_total = 7
        self._criar_tabelas()
        self._atualizar_progresso()

    def _criar_tabelas(self):
        os.makedirs(os.path.dirname(CAMINHO_DB), exist_ok=True)
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS rotina (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            hora_minuto INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            bateria INTEGER NOT NULL,
            tempo_tela INTEGER NOT NULL DEFAULT 0,
            app_ativo TEXT DEFAULT 'Nenhum',
            UNIQUE(data, hora_minuto)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS controle_aprendizado (
            data TEXT PRIMARY KEY,
            registros_hoje INTEGER DEFAULT 0,
            validado INTEGER DEFAULT 0
        )''')
        conn.commit()
        conn.close()

    def _atualizar_progresso(self):
        try:
            conn = sqlite3.connect(CAMINHO_DB)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM controle_aprendizado WHERE validado = 1')
            self.dias_treinados = c.fetchone()[0]
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao ler progresso: {e}")

    @property
    def fase_aprendizado_ativa(self):
        return self.dias_treinados < self.dias_total

    def registrar_leitura(self, lat, lon, bateria, tempo_tela, app_ativo):
        agora = datetime.now()
        data_str = agora.strftime("%Y-%m-%d")
        hora_minuto = agora.hour * 60 + agora.minute

        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        try:
            c.execute('''INSERT OR REPLACE INTO rotina 
                (data, hora_minuto, latitude, longitude, bateria, tempo_tela, app_ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (data_str, hora_minuto, lat, lon, bateria, tempo_tela, app_ativo))

            c.execute('INSERT OR IGNORE INTO controle_aprendizado (data, registros_hoje, validado) VALUES (?, 0, 0)', (data_str,))
            c.execute('UPDATE controle_aprendizado SET registros_hoje = registros_hoje + 1 WHERE data = ?', (data_str,))
            
            c.execute('SELECT registros_hoje, validado FROM controle_aprendizado WHERE data = ?', (data_str,))
            reg, val = c.fetchone()
            if reg >= 20 and val == 0:
                # CORREÇÃO: Usando a coluna 'validado' declarada no banco
                c.execute('UPDATE controle_aprendizado SET validado = 1 WHERE data = ?', (data_str,))
                self.dias_treinados += 1

            conn.commit()
            limite_data = (agora - timedelta(days=15)).strftime("%Y-%m-%d")
            c.execute('DELETE FROM rotina WHERE data < ?', (limite_data,))
            conn.commit()
        except Exception as e:
            print(f"⚠️ Erro IA Banco: {e}")
        finally:
            conn.close()

    def verificar_anomalia(self, lat, lon, bateria, tempo_tela):
        if self.fase_aprendizado_ativa:
            return 0, f"Modo Estudo Ativo ({self.dias_treinados}/{self.dias_total} Dias). Analisando perfil..."

        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('SELECT latitude, longitude, hora_minuto, bateria, tempo_tela FROM rotina')
        dados = c.fetchall()
        conn.close()

        if len(dados) < 30:
            return 0, "Aguardando volume de dados mínimo para inferência preditiva."

        X = np.array(dados)
        ia = IsolationForest(contamination=0.05, random_state=42)
        ia.fit(X)
        
        agora = datetime.now()
        hora_minuto = agora.hour * 60 + agora.minute
        pred = ia.predict([[lat, lon, hora_minuto, bateria, tempo_tela]])
        
        if pred[0] == -1:
            return 1, "⚠️ ANOMALIA DE ROTINA DETECTADA!"
        return 0, "Dentro da normalidade."
      
