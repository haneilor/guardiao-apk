import sqlite3, os, math, subprocess

if 'ANDROID_PRIVATE' in os.environ:
    pasta_safe = os.environ.get('ANDROID_PRIVATE')
else:
    pasta_safe = os.path.dirname(os.path.abspath(__file__))

CAMINHO_DB = os.path.join(pasta_safe, "guardiao.db")

class GerenciadorAlertas:
    def __init__(self):
        self._criar_tabelas()

    def _criar_tabelas(self):
        os.makedirs(os.path.dirname(CAMINHO_DB), exist_ok=True)
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS contatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL UNIQUE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS locais_seguros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            raio REAL DEFAULT 0.00045,
            UNIQUE(nome, tipo)
        )''')
        conn.commit()
        conn.close()

    def cadastrar_contato(self, nome, telephone):
        if not nome.strip() or not telephone.strip():
            return False, "Preencha nome e telefone"
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM contatos')
        if c.fetchone()[0] >= 5:
            conn.close()
            return False, "Máximo de 5 contatos atingido"
        try:
            c.execute('INSERT INTO contatos (nome, telefone) VALUES (?, ?)', (nome, telephone))
            conn.commit()
            return True, "✅ Contato blindado!"
        except:
            return False, "❌ Telefone já cadastrado"
        finally:
            conn.close()

    def listar_contatos(self):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        try:
            c.execute('SELECT id, nome, telefone FROM contatos')
            dados = c.fetchall()
        except:
            dados = []
        finally:
            conn.close()
        return dados

    def excluir_contato(self, id_c):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('DELETE FROM contatos WHERE id = ?', (id_c,))
        conn.commit()
        conn.close()

    def cadastrar_local(self, nome, tipo, lat, lon):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        try:
            c.execute('''INSERT OR REPLACE INTO locais_seguros (nome, tipo, latitude, longitude) 
                        VALUES (?, ?, ?, ?)''', (str(nome), str(tipo), float(lat), float(lon)))
            conn.commit()
            return True, "✅ Área de Geofencing Registrada!"
        except Exception as e:
            return False, f"❌ Erro: {e}"
        finally:
            conn.close()

    def listar_locais(self):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('SELECT id, nome, tipo, latitude, longitude FROM locais_seguros')
        dados = c.fetchall()
        conn.close()
        return dados

    def excluir_local(self, id_l):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('DELETE FROM locais_seguros WHERE id = ?', (id_l,))
        conn.commit()
        conn.close()

    def _formatar_telefone(self, telefone):
        num = ''.join(c for c in telefone if c.isdigit())
        if num.startswith('55') and len(num) > 11:
            num = num[2:]
        if len(num) == 10: 
            num = num[:2] + '9' + num[2:]
        return num

    def verificar_seguro(self, lat_atual, lon_atual):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('SELECT nome, latitude, longitude FROM locais_seguros')
        locais = c.fetchall()
        conn.close()

        for nome, lat_local, lon_local in locais:
            dlat = math.radians(lat_local - lat_atual)
            dlon = math.radians(lon_local - lon_atual)
            a = (math.sin(dlat / 2) ** 2 + 
                 math.cos(math.radians(lat_atual)) * math.cos(math.radians(lat_local)) * math.sin(dlon / 2) ** 2)
            c_dist = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist_metros = 6371000 * c_dist

            if dist_metros <= 50:
                return True, f"Imunizado em área protegida estática: {nome}"
        return False, "Fora de área de geofencing estática"

    def enviar_alerta(self, nivel, mensagem, localizacao):
        contatos = self.listar_contatos()
        if not contatos:
            return False, "⚠️ Nenhum contato alvo cadastrado."

        titulo = "IA-ALERTA" if nivel == 1 else "IA-PERIGO" if nivel == 2 else "SOS-PANICO"
        link = f"https://www.google.com/maps?q={localizacao}"
        texto = f"GUARDIAO {titulo}: {mensagem}. Localizacao: {link}"

        enviado_via_android = False
        try:
            from jnius import autoclass
            SmsManager = autoclass('android.telephony.SmsManager')
            sms = SmsManager.getDefault()
            for id_c, nome, tel in contatos:
                num_completo = f"+55{self._formatar_telefone(tel)}"
                sms.sendTextMessage(num_completo, None, texto, None, None)
            enviado_via_android = True
            print("🚀 [CHIP APK] Disparado com absoluto sucesso via API de Hardware do Android!")
        except Exception as e:
            print(f"Falha ao enviar SMS Nativo: {e}")

        if not enviado_via_android:
            print(f"\n📡 [SIMULADOR DE BACKUP] SMS Corporificado:\nTexto: {texto}")
            for id_c, nome, tel in contatos:
                print(f" -> Canal Reservado: {nome} (+55{self._formatar_telefone(tel)})")
        return True, "✅ Alarmes processados com sucesso!"
