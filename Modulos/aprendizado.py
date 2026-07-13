import sqlite3, os, numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest

CAMINHO_DB = "/root/guardiao_app/guardiao.db"

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
        # Nova tabela de rotina incluindo tempo de tela e apps ativos
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
        # Tabela para controlar o histórico de dias válidos de coleta
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
        except:
            self.dias_treinados = 0

    @property
    def fase_aprendizado_ativa(self):
        self._atualizar_progresso()
        return self.dias_treinados < self.dias_total

    def registrar_leitura(self, lat, lon, bateria, tempo_tela, app_ativo):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        agora = datetime.now()
        data_str = agora.strftime("%Y-%m-%d")
        hora_minuto = agora.hour * 60 + agora.minute

        try:
            c.execute('''INSERT OR REPLACE INTO rotina 
                        (data, hora_minuto, latitude, longitude, bateria, tempo_tela, app_ativo)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                     (data_str, hora_minuto, float(lat), float(lon), int(bateria), int(tempo_tela), str(app_ativo)))
            
            c.execute('INSERT OR IGNORE INTO controle_aprendizado (data) VALUES (?)', (data_str,))
            c.execute('UPDATE controle_aprendizado SET registros_hoje = registros_hoje + 1 WHERE data = ?', (data_str,))
            
            # Se coletar pelo menos 20 amostras no dia, valida o dia como estudado
            c.execute('SELECT registros_hoje FROM controle_aprendizado WHERE data = ?', (data_str,))
            if c.fetchone()[0] >= 20:
                c.execute('UPDATE controle_aprendizado SET validated = 1 WHERE data = ?', (data_str,))
                
            conn.commit()
            # Limpeza automática: deleta dados com mais de 15 dias para economizar espaço
            limite_data = (agora - timedelta(days=15)).strftime("%Y-%m-%d")
            c.execute('DELETE FROM rotina WHERE data < ?', (limite_data,))
            conn.commit()
        except Exception as e:
            print(f"⚠️ Erro IA Banco: {e}")
        finally:
            conn.close()

    def verificar_anomalia(self, lat, lon, bateria, tempo_tela):
        # Se ainda estiver nos 7 dias de estudo, não gera alertas de proteção
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
        pred = ia.predict([[lat, lon, hora_minuto, bateria, tempo_tela]])[0]
        
        if pred == -1:
            return 2, "Anomalia de comportamento detectada (Incompatibilidade de rotina/uso de apps)."
        return 0, "Padrão de comportamento validado."
