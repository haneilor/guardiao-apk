import os, time, threading, subprocess, json, datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from modulos.aprendizado import AprendizRotina
from modulos.notificacoes import GerenciadorAlertas

app = Flask(__name__)
rotina = AprendizRotina()
alertas = GerenciadorAlertas()

monitoramento_ativo = False
thread_monitor = None
ultima_localizacao_valida = (-15.5961, -56.0967)

def capturar_telemetria_android():
    tempo_tela_minutos = 15
    app_topo = "Nenhum"
    try:
        tempo_tela_minutos = int(datetime.datetime.now().minute)
        app_topo = "WhatsApp" if tempo_tela_minutos % 2 == 0 else "Navegador"
    except:
        pass
    return tempo_tela_minutos, app_topo

def pegar_localizacao_e_bateria():
    global ultima_localizacao_valida
    lat, lon = ultima_localizacao_valida
    bateria = 50
    try:
        res_bat = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=3)
        if res_bat.returncode == 0:
            bateria = int(json.loads(res_bat.stdout).get("percentage", 50))
    except:
        pass
    try:
        res = subprocess.run(["termux-location", "-p", "gps", "-r", "once"], capture_output=True, text=True, timeout=4)
        if res.returncode == 0 and res.stdout.strip():
            dados = json.loads(res.stdout)
            lat, lon = float(dados.get("latitude")), float(dados.get("longitude"))
            ultima_localizacao_valida = (lat, lon)
            return lat, lon, battery
    except:
        pass
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
    global monitoramento_ativo
    print("🚀 Motor de IA Iniciado com Gerenciamento Inteligente de Bateria...")
    intervalo_atual = 45
    while monitoramento_ativo:
        try:
            lat, lon, battery = pegar_localizacao_e_bateria()
            tempo_tela, app_ativo = capturar_telemetria_android()
            rotina.registrar_leitura(lat, lon, battery, tempo_tela, app_ativo)
            seguro, msg_seguro = alertas.verificar_seguro(lat, lon)
            if seguro:
                print(f"🔋 [Modo Eco]: Em Zona Segura ({msg_seguro}). Checagem a cada 5 min.")
                intervalo_atual = 300
            else:
                nivel, msg_ia = rotina.verificar_anomalia(lat, lon, battery, tempo_tela)
                print(f"🧠 [Análise Cognitiva IA]: {msg_ia}")
                if nivel > 0:
                    alertas.enviar_alerta(nivel, msg_ia, f"{lat:.6f},{lon:.6f}")
                    intervalo_atual = 45
                else:
                    intervalo_atual = 60
        except Exception as e:
            print(f"❌ Erro no ciclo de monitoramento: {e}")
            intervalo_atual = 90
        time.sleep(intervalo_atual)

@app.route('/')
def index():
    contatos = alertas.listar_contatos()
    locais = alertas.listar_locais()
    progresso = f"{rotina.dias_treinados}/{rotina.dias_total}D"
    return render_template('index.html', ativo=monitoramento_ativo, contatos=contatos, locais=locais, progresso=progresso)

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
    loc_str = f"{lat:.6f},{lon:.6f}"
    _, msg = alertas.enviar_alerta(3, "🆘 ALERTA MÁXIMO: PÂNICO ATIVADO!", loc_str)
    return jsonify({"ok": True, "mensagem": msg})

# --- INICIALIZAÇÃO ADAPTADA PARA ANDROID (WEBVIEW + FLASK) ---

def rodar_servidor_flask():
    # Executa o servidor Flask localmente em background
    app.run(host='127.0.0.1', port=5000, debug=False)

if __name__ == '__main__':
    # 1. Inicia o Flask numa linha de execução paralela (Thread)
    threading.Thread(target=rodar_servidor_flask, daemon=True).start()
    
    # 2. Aguarda um momento para o servidor Flask ligar com sucesso
    time.sleep(1.5)
    
    # 3. Inicia a interface Kivy como um navegador WebView em ecrã inteiro
    from kivy.app import App
    from jnius import autoclass
    
    class GuardiaoApp(App):
        def build(self):
            # Aciona as funções nativas de visualização do Android
            Activity = autoclass('org.kivy.android.PythonActivity').mActivity
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            
            webview = WebView(Activity)
            webview.getSettings().setJavaScriptEnabled(True)
            webview.getSettings().setDomStorageEnabled(True) # Essencial para persistência HTML5
            webview.setWebViewClient(WebViewClient())
            
            # Conecta o ecrã do telemóvel ao servidor Flask interno
            webview.loadUrl('http://127.0.0.1:5000/')
            return webview

    # Executa a janela principal no telemóvel
    GuardiaoApp().run()
                               
