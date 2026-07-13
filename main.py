import os
import time
import threading
import json
import datetime
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, jsonify
from modulos.aprendizado import AprendizRotina
from modulos.notificacoes import GerenciadorAlertas

# --- Inicialização do Flask ---
app = Flask(__name__)
rotina = AprendizRotina()
alertas = GerenciadorAlertas()

monitoramento_ativo = False
thread_monitor = None
ultima_localizacao_valida = (-15.5961, -56.0967)

def solicitar_permissoes_android():
    """
    Solicita as permissões em tempo de execução necessárias para o Android 12, 13 e 14.
    """
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.SEND_SMS,
            Permission.ACCESS_FINE_LOCATION,
            Permission.ACCESS_COARSE_LOCATION,
            Permission.POST_NOTIFICATIONS
        ])
        print("✅ Permissões solicitadas ao sistema Android.")
    except ImportError:
        # Ignora se estiver a rodar fora do ambiente Android (ex: computador local)
        pass

def capturar_telemetria_android():
    """
    Simula a captura do tempo de ecrã e da aplicação ativa.
    """
    tempo_tela_minutos = 15
    app_topo = "Nenhum"
    try:
        tempo_tela_minutos = int(datetime.datetime.now().minute)
        app_topo = "WhatsApp" if tempo_tela_minutos % 2 == 0 else "Navegador"
    except:
        pass
    return tempo_tela_minutos, app_topo

def pegar_localizacao_e_bateria():
    """
    Captura dados de telemetria diretamente das APIs de hardware do Android via JNIUS.
    Possui mecanismos de fallback (Termux e Geolocalização por IP) se o GPS falhar.
    """
    global ultima_localizacao_valida
    lat, lon = ultima_localizacao_valida
    bateria = 50

    # 1. Tentar obter do Android Nativo via JNIUS (Buildozer APK)
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        context = PythonActivity.mActivity

        # Obter nível da bateria nativamente
        IntentFilter = autoclass('android.content.IntentFilter')
        Intent = autoclass('android.content.Intent')
        filter_bat = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        battery_status = context.registerReceiver(None, filter_bat)
        
        level = battery_status.getIntExtra("level", -1)
        scale = battery_status.getIntExtra("scale", -1)
        if level != -1 and scale != -1:
            bateria = int((level / float(scale)) * 100)

        # Obter geolocalização nativa
        LocationManager = autoclass('android.location.LocationManager')
        Context = autoclass('android.content.Context')
        
        locator = context.getSystemService(Context.LOCATION_SERVICE)
        localizacao_android = locator.getLastKnownLocation(LocationManager.GPS_PROVIDER)
        if not localizacao_android:
            localizacao_android = locator.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)

        if localizacao_android:
            lat = float(localizacao_android.getLatitude())
            lon = float(localizacao_android.getLongitude())
            ultima_localizacao_valida = (lat, lon)
            return lat, lon, bateria
    except Exception:
        # Se falhar ou não estiver no ambiente nativo APK, avança para os fallbacks
        pass

    # 2. Fallback do Termux (Legado)
    try:
        import subprocess
        res_bat = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=3)
        if res_bat.returncode == 0:
            bateria = int(json.loads(res_bat.stdout).get("percentage", 50))
    except:
        pass
    try:
        import subprocess
        res = subprocess.run(["termux-location", "-p", "gps", "-r", "once"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            dados = json.loads(res.stdout)
            lat = float(dados.get("latitude", lat))
            lon = float(dados.get("longitude", lon))
            ultima_localizacao_valida = (lat, lon)
            return lat, lon, bateria
    except:
        pass

    # 3. Fallback de Rede (Geolocalização por IP)
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://ip-api.com/json/", timeout=3)
        dados = json.loads(resp.read().decode('utf-8'))
        if dados.get("status") == "success":
            lat, lon = float(dados["lat"]), float(dados["lon"])
            ultima_localizacao_valida = (lat, lon)
    except:
        pass

    return lat, lon, bateria

def loop_monitoramento():
    """
    Loop que executa as análises da IA de 30 em 30 segundos em segundo plano.
    """
    global monitoramento_ativo
    print("🤖 Thread do Guardião IA inicializada com monitoramento ativo.")
    while monitoramento_ativo:
        try:
            lat, lon, bat = pegar_localizacao_e_bateria()
            tempo_tela, app_ativo = capturar_telemetria_android()
            
            # Registar no banco de dados para estudo de rotina
            rotina.registrar_leitura(lat, lon, bat, tempo_tela, app_ativo)
            
            # Validação 1: Geofencing
            seguro, local_nome = alertas.verificar_geofence(lat, lon)
            
            if not seguro:
                # Validação 2: Isolation Forest IA
                anomalia, msg = rotina.verificar_anomalia(lat, lon, bat, tempo_tela)
                if anomalia == 1:
                    localizacao_str = f"{lat:.6f},{lon:.6f}"
                    # Dispara alerta de perigo silencioso por anomalia
                    alertas.enviar_alerta(msg, localizacao_str, nivel=2)
            else:
                print(f"🟢 Seguro: Utilizador localizado em zona protegida ({local_nome}).")
        except Exception as e:
            print(f"⚠️ Erro no ciclo de varredura do Guardião: {e}")
        
        time.sleep(30)

# --- Rotas do Flask (Interface Web) ---

@app.route('/')
def index():
    lat, lon, bat = pegar_localizacao_e_bateria()
    seguro, local_nome = alertas.verificar_geofence(lat, lon)
    status_ia = "Estudando Rotinas" if rotina.fase_aprendizado_ativa else "IA Ativa e Operante"
    progresso = int((rotina.dias_treinados / rotina.dias_total) * 100)
    
    return render_template('index.html', 
                           bateria=bat, 
                           lat=f"{lat:.4f}", 
                           lon=f"{lon:.4f}",
                           geofence="Seguro" if seguro else "Fora de Área Segura",
                           local_atual=local_nome,
                           status_ia=status_ia,
                           progresso_treino=progresso,
                           contatos=alertas.listar_contatos(),
                           locais=alertas.listar_locais(),
                           monitor_ativo=monitoramento_ativo)

@app.route('/excluir-contato/<int:id_c>')
def exc_c(id_c):
    alertas.excluir_contato(id_c)
    return redirect(url_for('index'))

@app.route('/salvar-local/<string:tipo>')
def cad_l(tipo):
    lat, lon, _ = pegar_localizacao_e_bateria()
    alertas.cadastrar_local(f"Meu {tipo}", tipo, lat, lon)
    return redirect(url_for('index'))

@app.route('/excluir-local/<int:id_l>')
def exc_l(id_l):
    alertas.excluir_local(id_l)
    return redirect(url_for('index'))

@app.route('/salvar-contato', methods=['POST'])
def cad_cont():
    n = request.form['nome'].strip()
    t = request.form['telefone'].strip()
    alertas.cadastrar_contato(n, t)
    return redirect(url_for('index'))

@app.route('/iniciar', methods=['POST'])
def iniciar():
    global monitoramento_ativo, thread_monitor
    if not monitoramento_ativo:
        monitoramento_ativo = True
        thread_monitor = threading.Thread(target=loop_monitoramento, daemon=True)
        thread_monitor.start()
    return jsonify({"ok": True, "mensagem": "🟢 Guardião IA Iniciado com Sucesso!"})

@app.route('/parar', methods=['POST'])
def parar():
    global monitoramento_ativo
    monitoramento_ativo = False
    return jsonify({"ok": True, "mensagem": "⏸️ Monitoramento de IA suspenso."})

@app.route('/panico', methods=['POST'])
def panico():
    lat, lon, _ = pegar_localizacao_e_bateria()
    localizacao_str = f"{lat:.6f},{lon:.6f}"
    alertas.enviar_alerta("BOTAO DE PANICO PRESSIONADO! PRECISO DE AJUDA URGENTE!", localizacao_str, nivel=3)
    return jsonify({"ok": True, "mensagem": "🚨 ALERTA DE PÂNICO DISPARADO IMEDIATAMENTE!"})


# --- Kivy Bootstrap (Interface Nativa e Execução Android) ---

from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock

class GuardiaoApp(App):
    def build(self):
        # 1. Solicitar permissões nativas do Android assim que o app carregar
        solicitar_permissoes_android()
        
        # 2. Iniciar o servidor Flask em segundo plano
        def rodar_flask():
            # Roda na porta 5000 em localhost para manter a comunicação interna segura
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
            
        threading.Thread(target=rodar_flask, daemon=True).start()
        
        # 3. Agendar a abertura automática do painel no navegador padrão do Android
        def abrir_painel_visual(dt):
            webbrowser.open("http://127.0.0.1:5000")
            
        Clock.schedule_once(abrir_painel_visual, 1.5)
        
        # Retorna um ecrã de carregamento simples do Kivy para o utilizador
        return Label(text="🛡️ Guardião IA Ativo em Segundo Plano.\nRedirecionando para o painel de controlo...")

if __name__ == '__main__':
    GuardiaoApp().run()
      
