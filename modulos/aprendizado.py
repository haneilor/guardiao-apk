import sqlite3, os, math
from datetime import datetime, timedelta

if 'ANDROID_PRIVATE' in os.environ:
    pasta_safe = os.environ.get('ANDROID_PRIVATE')
else:
    pasta_safe = os.path.dirname(os.path.abspath(__file__))

CAMINHO_DB = os.path.join(pasta_safe, "guardiao.db")

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
            
            c.execute('SELECT registros_hoje FROM controle_aprendizado WHERE data = ?', (data_str,))
            if c.fetchone()[0] >= 20:
                c.execute('UPDATE controle_aprendizado SET validado = 1 WHERE data = ?', (data_str,))
                
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
        c.execute('SELECT latitude, longitude, bateria, tempo_tela FROM rotina')
        dados = c.fetchall()
        conn.close()

        if len(dados) < 30:
            return 0, "Aguardando volume de dados mínimo para inferência preditiva."

        # Motor Estatístico de Desvio Padrão (Substitui o IsolationForest de forma leve)
        total = len(dados)
        media_lat = sum(d[0] for d in dados) / total
        media_lon = sum(d[1] for d in dados) / total
        media_tela = sum(d[3] for d in dados) / total

        # Calcula a distância da localização atual para a média histórica (Geofencing Dinâmico)
        dlat = math.radians(media_lat - lat)
        dlon = math.radians(media_lon - lon)
        a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(media_lat)) * math.sin(dlon / 2) ** 2)
        dist_media_metros = 6371000 * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

        # Se o usuário estiver a mais de 15km da sua área histórica comum ou o tempo de tela explodir
        if dist_media_metros > 15000 or tempo_tela > (media_tela * 3):
            return 2, "Anomalia detectada: Fora do perímetro geográfico habitual do perfil."
            
        return 0, "Padrão de comportamento validado."
  
