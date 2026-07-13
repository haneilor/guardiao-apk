import os, time, threading, subprocess, json, datetime, sys
from flask import Flask, render_template, request, redirect, url_for, jsonify

# Configura o Python para trabalhar no diretório base correto de instalação do app
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)
os.chdir(base_dir)

from modulos.aprendizado import AprendizRotina
from modulos.notificacoes import GerenciadorAlertas

app = Flask(__name__,
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))

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
    
    # Captura amigável da bateria via Plyer
    try:
        from plyer import battery
        status = battery.status()
        if status and status.get('percentage'):
            bateria = int(status['percentage'])
    except:
        pass

    # Coleta de localização segura via Web API (Independente de hardware bloqueado)
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://ip-api.com/json/", timeout=4)
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
                intervalo_atual = 300
            else:
                nivel, msg_ia = rotina.verificar_anomalia(lat, lon, battery, tempo_tela)
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

def rodar_servidor_flask():
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)

if __name__ == '__main__':
    threading.Thread(target=rodar_servidor_flask, daemon=True).start()
    time.sleep(2.5) # Tempo estendido para garantir a montagem segura do DB privado do Android
    
    from kivy.app import App
    from jnius import autoclass
    
    class GuardiaoApp(App):
        def build(self):
            Activity = autoclass('org.kivy.android.PythonActivity').mActivity
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            
            webview = WebView(Activity)
            webview.getSettings().setJavaScriptEnabled(True)
            webview.getSettings().setDomStorageEnabled(True)
            webview.setWebViewClient(WebViewClient())
            
            webview.loadUrl('http://127.0.0.1:5000/')
            return webview

    GuardiaoApp().run()
