[app]
title = Guardiao IA
package.name = guardiaoia
package.domain = org.guardiao
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,css,js
source.include_patterns = templates/*, modulos/*
version = 1.0.0
requirements = python3,hostpython3,kivy,flask,numpy,scikit-learn,pyjnius

orientation = portrait
fullscreen = 0

# Declaração estrita de permissões do Android moderno
android.permissions = INTERNET, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, SEND_SMS, RECEIVE_BOOT_COMPLETED, FOREGROUND_SERVICE, POST_NOTIFICATIONS
android.features = android.hardware.telephony
android.api = 34
android.minapi = 21
android.ndk_api = 21
android.private_storage = True

# Definição obrigatória para serviços persistentes em background no Android 14
android.foreground_service_types = location, special_use

[buildozer]
log_level = 2
warn_on_root = 1
