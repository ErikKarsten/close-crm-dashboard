#!/usr/bin/env python3
"""
Close CRM Vertriebler Performance Dashboard - Version 2.0
Detailliertes Reporting mit Sales-Funnel Metriken

Installation: pip install streamlit plotly pandas
Start: streamlit run close_dashboard.py
"""

import streamlit as st
import base64
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, date
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ═════════════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Close CRM Vertrieb Dashboard",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_URL = "https://api.close.com/api/v1"

# Sales Funnel Status IDs
STATUS_CONFIG = {
    # Einstiegsstatus
    "mql": "stat_2FYhYKsjo2eicEJ4sXfKlBiHOyUfRrBeqQe4N77R0j7",
    "positive_mail_lead": "stat_k829Dd4u5xTv24UXY6DPKo4noz6UE3Jy7ErPcXvExH",
    
    # Qualifizierung
    "sekr_erreicht": "stat_CVoVCgANu7tAYwSFZ0Pw6gDiABhLtjLmoh4Zp94iYAj",  # Sekretariat erreicht
    "nicht_erreicht": "stat_40IUqr1pzh1LplvaVFkS04jgiqKI70mwiZLce5KdPwE",
    
    # Entscheider Level
    "entscheider_kein_interesse": "stat_bzh9jBOUMAJDN195VRrohErSuu6vTF4CofzipoOtOtF",  # Kein Interesse (Entscheider)
    
    # Terminierungen pro Person
    "quali_terminiert_enes": "stat_c1U5gf7ObGY5VIvxchio6AFmtKvhdjst4lG3Bo3hxoU",
    "quali_terminiert_luk": "stat_6JP3mHvQnVmEUpOgdDcLy0YnB8ZN3ubqzFZSqRz3Mih",
    "quali_terminiert_sebastian": "stat_vKldwcyB9741E8NX3TA3qkRDJagRzFIOXLW3abkHW6v",
    
    # No Show
    "no_show_qc": "stat_2TXvU9dFI9aRV1GDcbGfsBVR1bZiImfzip3EakHDBTV",
    
    # SC Terminiert
    "sc_terminiert": "stat_5jesGtifrv9ULOXq3ssvUplls0teGJDiCW4c8ypYBWg",
}

# User Konfiguration
USERS = {
    "enes": {
        "id": "user_VphQt8gFT3hQbr9R52A51CQSA6eV6UeyKgnz3iCEZGe",
        "name": "Enes Erdogan",
        "termin_status": STATUS_CONFIG["quali_terminiert_enes"],
    },
    "luk": {
        "id": "user_7AYoeKx6OLtlpDYQC3EBPJRKUgFnXExtqEaLeSmXIuJ",
        "name": "Luk Gittner",
        "termin_status": STATUS_CONFIG["quali_terminiert_luk"],
    },
    "sebastian": {
        "id": "user_VdH6KwSarmfoVgEO2ZgchCf7mkyjK9mO6LPEVenllXb",
        "name": "Sebastian Sturm",
        "termin_status": STATUS_CONFIG["quali_terminiert_sebastian"],
    },
}

# Status Labels für Anzeige
STATUS_LABELS = {
    STATUS_CONFIG["sekr_erreicht"]: "Sekretariat erreicht",
    STATUS_CONFIG["entscheider_kein_interesse"]: "Kein Interesse (Entscheider)",
    STATUS_CONFIG["quali_terminiert_enes"]: "Quali terminiert (kalt Enes)",
    STATUS_CONFIG["quali_terminiert_luk"]: "Quali terminiert (kalt Luk)",
    STATUS_CONFIG["quali_terminiert_sebastian"]: "Quali kalt terminiert (Sebastian)",
    STATUS_CONFIG["no_show_qc"]: "No Show QC",
    STATUS_CONFIG["sc_terminiert"]: "SC Terminiert",
}


# ═════════════════════════════════════════════════════════════════════════════
# API KLASSE
# ═════════════════════════════════════════════════════════════════════════════

class CloseAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        auth_str = base64.b64encode(f"{api_key}:".encode()).decode()
        self.auth_header = f"Basic {auth_str}"

    @st.cache_data(ttl=300)
    def _get_cached(_self, endpoint: str, params_tuple: tuple) -> Dict:
        """Cached API Call"""
        url = f"{BASE_URL}/{endpoint}"
        if params_tuple:
            params = dict(params_tuple)
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        
        req = urllib.request.Request(
            url,
            headers={"Authorization": _self.auth_header, "Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    def get_all_activities(self, date_from: str, date_to: str, 
                          activity_type: Optional[str] = None) -> List[Dict]:
        """Fetch alle Activities mit Pagination"""
        activities = []
        skip = 0
        limit = 100
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        batch_num = 0
        while True:
            params = {
                "date_created__gte": date_from,
                "date_created__lte": date_to,
                "_limit": str(limit),
                "_skip": str(skip),
            }
            
            status_text.text(f"Lade Daten... Batch {batch_num + 1}")
            
            try:
                data = self._get_cached("activity/", tuple(sorted(params.items())))
                batch = data.get("data", [])
            except Exception as e:
                status_text.empty()
                progress_bar.empty()
                st.error(f"API Fehler: {e}")
                break
            
            if not batch:
                break
            
            if activity_type:
                filtered = [a for a in batch if a.get("_type") == activity_type]
                activities.extend(filtered)
            else:
                activities.extend(batch)
            
            progress_bar.progress(min((skip + len(batch)) / 2000, 0.99))
            
            if len(batch) < limit:
                break
            
            skip += limit
            batch_num += 1
            
            # Safety break nach 20 batches
            if batch_num > 20:
                break
        
        progress_bar.empty()
        status_text.empty()
        return activities


# ═════════════════════════════════════════════════════════════════════════════
# DATENVERARBEITUNG
# ═════════════════════════════════════════════════════════════════════════════

class DashboardData:
    def __init__(self, api: CloseAPI):
        self.api = api
    
    def calculate_call_metrics(self, calls: List[Dict]) -> Dict:
        """Berechne Call-Metriken"""
        if not calls:
            return {
                "total_calls": 0, "connected_calls": 0, "failed_calls": 0,
                "cancelled": 0, "no_answer": 0, "busy": 0,
                "total_duration_seconds": 0, "avg_duration_seconds": 0,
                "avg_duration_connected": 0, "total_talk_time_minutes": 0,
                "connection_rate_percent": 0,
            }
        
        total = len(calls)
        connected = [c for c in calls if c.get("status") == "completed" and c.get("duration", 0) > 0]
        failed = [c for c in calls if c.get("status") == "failed"]
        cancelled = [c for c in calls if c.get("status") == "cancel"]
        no_answer = [c for c in calls if c.get("status") == "no-answer"]
        busy = [c for c in calls if c.get("status") == "busy"]
        
        durations = [c.get("duration", 0) or 0 for c in calls]
        connected_durations = [c.get("duration", 0) or 0 for c in connected]
        
        total_duration = sum(durations)
        avg_duration = total_duration / total if total > 0 else 0
        avg_connected = sum(connected_durations) / len(connected) if connected else 0
        
        return {
            "total_calls": total,
            "connected_calls": len(connected),
            "failed_calls": len(failed),
            "cancelled": len(cancelled),
            "no_answer": len(no_answer),
            "busy": len(busy),
            "total_duration_seconds": total_duration,
            "avg_duration_seconds": round(avg_duration, 1),
            "avg_duration_connected": round(avg_connected, 1),
            "total_talk_time_minutes": round(total_duration / 60, 1),
            "connection_rate_percent": round(len(connected) / total * 100, 1) if total > 0 else 0,
        }
    
    def get_data_for_date(self, selected_date: date) -> Tuple[Dict, Dict]:
        """
        Hole alle Daten für ein Datum
        Returns: (user_data, team_totals)
        """
        date_str = selected_date.strftime("%Y-%m-%d")
        date_from = f"{date_str}T00:00:00"
        date_to = f"{date_str}T23:59:59"
        
        # Lade Daten
        with st.spinner("Lade Status-Changes..."):
            status_changes = self.api.get_all_activities(date_from, date_to, "LeadStatusChange")
        
        with st.spinner("Lade Calls..."):
            all_activities = self.api.get_all_activities(date_from, date_to)
        
        calls = [a for a in all_activities if a.get("_type") == "Call"]
        
        # Calls nach User gruppieren
        calls_by_user = defaultdict(list)
        for call in calls:
            user_id = call.get("user_id")
            if user_id:
                calls_by_user[user_id].append(call)
        
        # Status Changes nach User und Typ analysieren
        user_metrics = {}
        
        for user_key, user_config in USERS.items():
            user_id = user_config["id"]
            user_name = user_config["name"]
            user_termin_status = user_config["termin_status"]
            
            user_calls = calls_by_user.get(user_id, [])
            call_metrics = self.calculate_call_metrics(user_calls)
            
            # Zähle verschiedene Status-Changes
            sekr_erreicht = 0
            entscheider_kein_interesse = 0
            termine_gelegt = 0
            no_shows = 0
            sc_terminiert_count = 0
            qc_gefuehrt = 0
            leads_mit_quali_vorher = []
            
            for activity in status_changes:
                if activity.get("user_id") != user_id:
                    continue
                
                new_status = activity.get("new_status_id")
                old_status_label = activity.get("old_status_label", "")
                old_status_id = activity.get("old_status_id", "")
                
                # Sekretariat erreicht (an VZ gescheitert)
                if new_status == STATUS_CONFIG["sekr_erreicht"]:
                    sekr_erreicht += 1
                
                # Kein Interesse Entscheider (an Entscheider gescheitert)
                if new_status == STATUS_CONFIG["entscheider_kein_interesse"]:
                    entscheider_kein_interesse += 1
                
                # Termine gelegt (Quali terminiert für diese Person)
                if new_status == user_termin_status:
                    termine_gelegt += 1
                    leads_mit_quali_vorher.append(activity.get("lead_id"))
                
                # No Show (nur wenn vorher Quali terminiert von DIESER Person war)
                if new_status == STATUS_CONFIG["no_show_qc"]:
                    # Prüfe ob dieser Lead zuvor von dieser Person terminiert wurde
                    # (Hier vereinfacht: Zähle alle No Shows)
                    no_shows += 1
                
                # SC terminiert
                if new_status == STATUS_CONFIG["sc_terminiert"]:
                    sc_terminiert_count += 1
                
                # QC geführt (vorher alles mit "Quali terminiert")
                if "quali terminiert" in old_status_label.lower() or "quali_terminiert" in str(old_status_id):
                    qc_gefuehrt += 1
            
            # Berechne Quoten
            brutto_to_termin = round(termine_gelegt / call_metrics["total_calls"] * 100, 1) if call_metrics["total_calls"] > 0 else 0
            brutto_connected = call_metrics["connection_rate_percent"]
            vz_failed_rate = round(sekr_erreicht / call_metrics["total_calls"] * 100, 1) if call_metrics["total_calls"] > 0 else 0
            entscheider_failed_rate = round(entscheider_kein_interesse / call_metrics["total_calls"] * 100, 1) if call_metrics["total_calls"] > 0 else 0
            
            # Entscheider erreicht = Sekretariat durchgekommen (verbunden - sekr erreicht)
            entscheider_erreicht = max(0, call_metrics["connected_calls"] - sekr_erreicht)
            brutto_to_entscheider = round(entscheider_erreicht / call_metrics["total_calls"] * 100, 1) if call_metrics["total_calls"] > 0 else 0
            entscheider_to_termin = round(termine_gelegt / entscheider_erreicht * 100, 1) if entscheider_erreicht > 0 else 0
            
            user_metrics[user_key] = {
                "name": user_name,
                "calls": call_metrics,
                "sekr_erreicht": sekr_erreicht,
                "entscheider_kein_interesse": entscheider_kein_interesse,
                "termine_gelegt": termine_gelegt,
                "no_shows": no_shows,
                "sc_terminiert": sc_terminiert_count,
                "qc_gefuehrt": qc_gefuehrt,
                # Quoten
                "brutto_to_termin": brutto_to_termin,
                "brutto_connected": brutto_connected,
                "vz_failed_rate": vz_failed_rate,
                "entscheider_failed_rate": entscheider_failed_rate,
                "brutto_to_entscheider": brutto_to_entscheider,
                "entscheider_to_termin": entscheider_to_termin,
                "entscheider_erreicht": entscheider_erreicht,
                "calls_per_termin": round(call_metrics["total_calls"] / termine_gelegt, 1) if termine_gelegt > 0 else 0,
            }
        
        # Team Gesamtwerte
        team_totals = {
            "total_calls": sum(m["calls"]["total_calls"] for m in user_metrics.values()),
            "total_connected": sum(m["calls"]["connected_calls"] for m in user_metrics.values()),
            "total_sekr": sum(m["sekr_erreicht"] for m in user_metrics.values()),
            "total_kein_interesse": sum(m["entscheider_kein_interesse"] for m in user_metrics.values()),
            "total_termine": sum(m["termine_gelegt"] for m in user_metrics.values()),
            "total_no_shows": sum(m["no_shows"] for m in user_metrics.values()),
            "total_sc": sum(m["sc_terminiert"] for m in user_metrics.values()),
            "total_qc": sum(m["qc_gefuehrt"] for m in user_metrics.values()),
            "total_talk_time": sum(m["calls"]["total_talk_time_minutes"] for m in user_metrics.values()),
            "total_entscheider_erreicht": sum(m["entscheider_erreicht"] for m in user_metrics.values()),
        }
        
        # Team Quoten
        if team_totals["total_calls"] > 0:
            team_totals["brutto_to_termin"] = round(team_totals["total_termine"] / team_totals["total_calls"] * 100, 1)
            team_totals["brutto_connected"] = round(team_totals["total_connected"] / team_totals["total_calls"] * 100, 1)
            team_totals["vz_failed_rate"] = round(team_totals["total_sekr"] / team_totals["total_calls"] * 100, 1)
            team_totals["entscheider_failed_rate"] = round(team_totals["total_kein_interesse"] / team_totals["total_calls"] * 100, 1)
            team_totals["brutto_to_entscheider"] = round(team_totals["total_entscheider_erreicht"] / team_totals["total_calls"] * 100, 1)
        else:
            team_totals["brutto_to_termin"] = 0
            team_totals["brutto_connected"] = 0
            team_totals["vz_failed_rate"] = 0
            team_totals["entscheider_failed_rate"] = 0
            team_totals["brutto_to_entscheider"] = 0
        
        if team_totals["total_entscheider_erreicht"] > 0:
            team_totals["entscheider_to_termin"] = round(team_totals["total_termine"] / team_totals["total_entscheider_erreicht"] * 100, 1)
        else:
            team_totals["entscheider_to_termin"] = 0
        
        return user_metrics, team_totals


# ═════════════════════════════════════════════════════════════════════════════
# UI KOMPONENTEN
# ═════════════════════════════════════════════════════════════════════════════

def create_funnel_chart(user_data: Dict, user_key: str):
    """Erstelle Sales Funnel Chart für einen User"""
    data = user_data[user_key]
    
    fig = go.Figure(go.Funnel(
        y = ["Anwahlen", "Verbunden", "Sekr. Erreicht", "Entscheider OK", "Termine"],
        x = [
            data["calls"]["total_calls"],
            data["calls"]["connected_calls"],
            data["sekr_erreicht"],
            data["entscheider_erreicht"],
            data["termine_gelegt"],
        ],
        textinfo = "value+percent initial",
        marker = {"color": ["#e74c3c", "#f39c12", "#f1c40f", "#2ecc71", "#27ae60"]},
    ))
    
    fig.update_layout(
        title=f"Sales Funnel: {data['name']}",
        height=400,
        showlegend=False
    )
    
    return fig


def render_user_detail_card(user_key: str, data: Dict):
    """Render detaillierte User Card"""
    
    with st.expander(f"👤 {data['name']}", expanded=True):
        
        # ABSCHNITT 1: Anrufe
        st.markdown("### 📞 ANWAHLEN")
        cols = st.columns(4)
        with cols[0]:
            st.metric("Gesamt", data["calls"]["total_calls"])
        with cols[1]:
            st.metric("Verbunden", f"{data['calls']['connected_calls']} ({data['brutto_connected']}%)")
        with cols[2]:
            st.metric("Ø Dauer", f"{data['calls']['avg_duration_connected']}s")
        with cols[3]:
            st.metric("Sprechzeit", f"{data['calls']['total_talk_time_minutes']}min")
        
        # ABSCHNITT 2: Gescheitert
        st.markdown("### ❌ GESCHEITERT")
        cols2 = st.columns(2)
        with cols2[0]:
            st.metric("An VZ > Sekr. Erreicht", f"{data['sekr_erreicht']} ({data['vz_failed_rate']}%)")
        with cols2[1]:
            st.metric("An Entscheider > Kein Interesse", f"{data['entscheider_kein_interesse']} ({data['entscheider_failed_rate']}%)")
        
        # ABSCHNITT 3: Erfolge
        st.markdown("### ✅ ERFOLGE")
        cols3 = st.columns(4)
        with cols3[0]:
            st.metric("🎯 Termine", data["termine_gelegt"])
        with cols3[1]:
            st.metric("📋 QC geführt", data["qc_gefuehrt"])
        with cols3[2]:
            st.metric("🏃 No Shows", data["no_shows"])
        with cols3[3]:
            st.metric("📞 SC Terminiert", data["sc_terminiert"])
        
        # ABSCHNITT 4: Quoten
        st.markdown("### 📊 QUOTEN")
        quota_cols = st.columns(3)
        with quota_cols[0]:
            st.metric("Brutto → Termin", f"{data['brutto_to_termin']}%")
            st.metric("Brutto → Entscheider", f"{data['brutto_to_entscheider']}%")
        with quota_cols[1]:
            st.metric("Brutto → Verbunden", f"{data['brutto_connected']}%")
            st.metric("Entscheider → Termin", f"{data['entscheider_to_termin']}%")
        with quota_cols[2]:
            st.metric("Anrufe/Termin", data["calls_per_termin"])


def render_team_overview(team_totals: Dict):
    """Render Team Gesamtübersicht"""
    
    st.markdown("## 📈 TEAM GESAMT")
    
    # Hauptmetriken
    cols = st.columns(5)
    with cols[0]:
        st.metric("📞 Team-Anrufe", team_totals["total_calls"])
    with cols[1]:
        st.metric("✅ Verbunden", team_totals["total_connected"])
    with cols[2]:
        st.metric("🎯 Termine", team_totals["total_termine"])
    with cols[3]:
        st.metric("🏃 No Shows", team_totals["total_no_shows"])
    with cols[4]:
        st.metric("⏱️ Sprechzeit", f"{team_totals['total_talk_time']}min")
    
    # Gescheitert
    st.markdown("### ❌ TEAM: GESCHEITERT")
    cols2 = st.columns(2)
    with cols2[0]:
        st.metric("An VZ > Sekr. Erreicht", team_totals["total_sekr"])
    with cols2[1]:
        st.metric("An Entscheider > Kein Interesse", team_totals["total_kein_interesse"])
    
    # Erfolge
    st.markdown("### ✅ TEAM: ERFOLGE")
    cols3 = st.columns(3)
    with cols3[0]:
        st.metric("QC geführt", team_totals["total_qc"])
    with cols3[1]:
        st.metric("SC Terminiert", team_totals["total_sc"])
    with cols3[2]:
        st.metric("Entscheider erreicht", team_totals["total_entscheider_erreicht"])
    
    # Team Quoten
    st.markdown("### 📊 TEAM QUOTEN")
    quota_cols = st.columns(5)
    with quota_cols[0]:
        st.metric("Brutto → Termin", f"{team_totals['brutto_to_termin']}%")
    with quota_cols[1]:
        st.metric("Brutto → Verbunden", f"{team_totals['brutto_connected']}%")
    with quota_cols[2]:
        st.metric("VZ gescheitert", f"{team_totals['vz_failed_rate']}%")
    with quota_cols[3]:
        st.metric("Entscheider gescheitert", f"{team_totals['entscheider_failed_rate']}%")
    with quota_cols[4]:
        st.metric("Entscheider → Termin", f"{team_totals['entscheider_to_termin']}%")


# ═════════════════════════════════════════════════════════════════════════════
# HAUPTANWENDUNG
# ═════════════════════════════════════════════════════════════════════════════

def get_api_key():
    """API Key aus Streamlit Secrets oder Eingabe"""
    try:
        return st.secrets["close_api_key"]
    except:
        return st.sidebar.text_input(
            "Close API Key",
            type="password",
            placeholder="api_...",
            help="Dein Close CRM API Key"
        )


def main():
    st.sidebar.title("🦞 Close CRM Dashboard")
    st.sidebar.markdown("---")
    
    api_key = get_api_key()
    
    if not api_key:
        st.sidebar.warning("⚠️ Bitte API Key eingeben")
        st.stop()
    
    # Datumsauswahl
    st.sidebar.subheader("📅 Zeitraum")
    selected_date = st.sidebar.date_input(
        "Datum auswählen",
        value=date.today(),
        max_value=date.today()
    )
    
    refresh = st.sidebar.button("🔄 Daten aktualisieren")
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Close CRM Dashboard v2.0")
    
    # Hauptbereich
    st.title(f"📊 Vertriebler Performance - {selected_date.strftime('%d.%m.%Y')}")
    
    # API initialisieren
    api = CloseAPI(api_key)
    dashboard = DashboardData(api)
    
    # Daten laden
    cache_key = f"{selected_date}_{refresh}"
    if cache_key not in st.session_state or refresh:
        user_data, team_totals = dashboard.get_data_for_date(selected_date)
        st.session_state["user_data"] = user_data
        st.session_state["team_totals"] = team_totals
        st.session_state["cache_key"] = cache_key
    else:
        user_data = st.session_state["user_data"]
        team_totals = st.session_state["team_totals"]
    
    if not user_data:
        st.error("Keine Daten gefunden")
        return
    
    # ═════════════════════════════════════════════════════════════════
    # TEAM GESAMT
    # ═════════════════════════════════════════════════════════════════
    render_team_overview(team_totals)
    
    st.markdown("---")
    
    # ═════════════════════════════════════════════════════════════════
    # EINZELNE VERTRIEBLER
    # ═════════════════════════════════════════════════════════════════
    st.markdown("## 👤 EINZELREPORTING")
    
    for user_key, data in user_data.items():
        render_user_detail_card(user_key, data)
    
    # ═════════════════════════════════════════════════════════════════
    # EXPORT
    # ═════════════════════════════════════════════════════════════════
    st.markdown("---")
    
    if st.button("📥 CSV Export"):
        df_data = []
        for user_key, data in user_data.items():
            df_data.append({
                "Name": data["name"],
                "Datum": selected_date,
                "Anwahlen": data["calls"]["total_calls"],
                "Verbunden": data["calls"]["connected_calls"],
                "Verbindungsrate": data["brutto_connected"],
                "Sekr_Erreicht": data["sekr_erreicht"],
                "Entscheider_Kein_Interesse": data["entscheider_kein_interesse"],
                "Termine": data["termine_gelegt"],
                "No_Shows": data["no_shows"],
                "QC_gefuehrt": data["qc_gefuehrt"],
                "SC_terminiert": data["sc_terminiert"],
                "Brutto_zu_Termin": data["brutto_to_termin"],
                "Entscheider_zu_Termin": data["entscheider_to_termin"],
                "Anrufe_pro_Termin": data["calls_per_termin"],
            })
        
        df = pd.DataFrame(df_data)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇️ CSV herunterladen",
            csv,
            f"close_report_{selected_date}.csv",
            "text/csv"
        )


if __name__ == "__main__":
    main()
