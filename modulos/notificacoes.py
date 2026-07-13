import sqlite3, os, math, subprocess

BASE_DIR = os.environ.get('ANDROID_PRIVATE_DATA', os.path.dirname(os.path.abspath(__file__)))
CAMINHO_DB = os.path.join(BASE_DIR, "guardiao.db")

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
            return True, "Contato blindado cadastrado com sucesso!"
        except:
            return False, "Contato já cadastrado anteriormente"
        finally:
            conn.close()

    def excluir_contato(self, id_contato):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('DELETE FROM contatos WHERE id = ?', (id_contato,))
        conn.commit()
        conn.close()

    def listar_contatos(self):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('SELECT id, nome, telefone FROM contatos')
        res = c.fetchall()
        conn.close()
        return res

    def cadastrar_local(self, nome, tipo, lat, lon, raio=0.00045):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO locais_seguros (nome, tipo, latitude, longitude, raio) VALUES (?, ?, ?, ?, ?)',
                      (nome, tipo, lat, lon, raio))
            conn.commit()
        except Exception as e:
            print(f"Erro ao cadastrar local: {e}")
        finally:
            conn.close()

    def excluir_local(self, id_l):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('DELETE FROM locais_seguros WHERE id = ?', (id_l,))
        conn.commit()
        conn.close()

    def listar_locais(self):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('SELECT id, nome, tipo, latitude, longitude, raio FROM locais_seguros')
        res = c.fetchall()
        conn.close()
        return res

    def verificar_geofence(self, lat, lon):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('SELECT nome, latitude, longitude, raio FROM locais_seguros')
        locais = c.fetchall()
        conn.close()

        for nome, target_lat, target_lon, raio in locais:
            dist = math.sqrt((lat - target_lat)**2 + (lon - target_lon)**2)
            if dist <= raio:
                return True, nome
        return False, "Fora de Área Segura"

    def _formatar_telefone(self, tel):
        return "".join(filter(str.isdigit, tel))

    def enviar_alerta(self, mensagem, localizacao, nivel=1):
        conn = sqlite3.connect(CAMINHO_DB)
        c = conn.cursor()
        c.execute('SELECT id, nome, telefone FROM contatos')
        contatos = c.fetchall()
        conn.close()

        if not contatos:
            print("🚨 Alerta gerado, mas nenhum contato cadastrado.")
            return

        titulo = "IA-ALERTA" if nivel == 1 else "IA-PERIGO" if nivel == 2 else "SOS-PANICO"
        link = f"https://www.google.com/maps/search/?api=1&query={localizacao}"
        texto = f"GUARDIAO {titulo}: {mensagem}. Localizacao: {link}"

        enviado_via_android = False
        
        # Envio de SMS Silencioso e de Baixo Nível via APIs Java Nativa do Android
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            SmsManager = autoclass('android.telephony.SmsManager')
            
            try:
                # No Android 10+ o recomendado é obter o SMS Manager baseado no SubscriptionId do Chip padrão
                Context = autoclass('android.content.Context')
                sms_service = context.getSystemService(Context.TELEPHONY_SUBSYSTEM_SERVICE)
                sms = sms_service.getSmsManagerForSubscriptionId(sms_service.getDefaultSmsSubscriptionId())
            except Exception:
                sms = SmsManager.getDefault()
                
            for id_c, nome, tel in contatos:
                num_completo = f"+55{self._formatar_telefone(tel)}"
                # Dispara silenciosamente
                sms.sendTextMessage(num_completo, None, texto, None, None)
                
            enviado_via_android = True
            print("🚀 [CHIP APK] Disparado com absoluto sucesso de forma silenciosa via API de Hardware!")
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️ Falha no disparo nativo Android: {e}")

        # Fallback legados (Termux / Simulação local)
        if not enviado_via_android:
            try:
                for id_c, nome, tel in contatos:
                    num_completo = self._formatar_telefone(tel)
                    subprocess.run(["termux-sms-send", "-n", num_completo, texto], timeout=5)
                print("🚀 [CHIP TERMUX] Disparado via Hardware do Chip através do Termux-API!")
                enviado_via_android = True
            except:
                pass

        if not enviado_via_android:
            print(f"\\n📡 [SIMULADOR] SMS:\\nTexto: {texto}")
            for id_c, nome, tel in contatos:
                print(f" -> Canal simulado para: {nome} ({tel})")
      
