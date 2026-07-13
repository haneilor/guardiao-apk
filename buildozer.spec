[app]

# (str) Title of your application
title = Guardiao IA

# (str) Package name
package.name = myapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.test

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (leave empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,html,css,js

# (str) Application versioning
version = 0.1

# (list) Application requirements (UNIFICADO e adaptado para suportar Flask com WebView)
requirements = python3,kivy,sqlite3,flask,jinja2,pyjnius,android

# (list) Supported orientations
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = SEND_SMS, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, INTERNET

# (int) Target Android API
android.api = 33

# (int) Minimum API your APK / AAB will support
android.minapi = 24

# (int) Android NDK API to use
android.ndk_api = 24

# (str) Android NDK version to use
android.ndk = 25b

# (bool) If True, then automatically accept SDK license agreements.
android.accept_sdk_license = True

# (list) The Android archs to build for
android.archs = arm64-v8a

# (bool) enables Android auto backup feature
android.allow_backup = True

[buildozer]

# (int) Log level
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
