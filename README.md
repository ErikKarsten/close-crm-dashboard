# 📊 Close CRM Vertriebler Dashboard

Live-Dashboard zur Überwachung der Verkaufsteams-Performance.

## 🚀 Schnellstart

### 1. Lokal testen
```bash
pip install -r requirements.txt
streamlit run close_dashboard.py
```

### 2. Online deployen (Streamlit Cloud)
1. Dieses Repository zu GitHub pushen
2. Auf [share.streamlit.io](https://share.streamlit.io) anmelden
3. Repository auswählen
4. In den Secrets den Close API Key hinterlegen:
   ```toml
   [secrets]
   close_api_key = "dein_api_key_hier"
   ```

## 📋 Features

- 📅 Datumsauswahl mit Kalender
- 📞 Anruf-Statistiken pro Mitarbeiter
- 🎯 Terminierungs-Übersicht
- ⏱️ Durchschnittliche Gesprächsdauer
- 📊 Vergleichs-Charts
- 📥 CSV Export

## ⚙️ Konfiguration

Öffne `close_dashboard.py` und passe die User-IDs an:

```python
USERS = {
    "enes": "deine_user_id_aus_close",
    "sebastian": "deine_user_id_aus_close", 
    "luk": "deine_user_id_aus_close",
}
```

## 🔑 API Key

Der API Key wird auf sichere Weise verarbeitet:
- Lokal: Eingabe im Sidebar
- Cloud: Als Secret in Streamlit Cloud hinterlegt
