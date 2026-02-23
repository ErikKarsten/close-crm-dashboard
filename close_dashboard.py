#!/usr/bin/env python3
"""
Close CRM Vertriebler Performance Dashboard - Version 2.1
Optimierte Struktur: Einzelreporting vs. Team-Erfolgsmetriken
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

# Farbschema
COLORS = {
    "primary": "#3498db",
    "success": "#27ae60",
    "warning": "#f39c12",
    "danger": "#e74c3c",
    "info": "#9b59b6",
    "light": "#ecf0f1",
    "dark": "#2c3e50"
}

# Status IDs
STATUS_CONFIG = {
    "sekr_erreicht": "stat_CVoVCgANu7tAYwSFZ0Pw6gDiABhLtjLmoh4Zp94iYAj",
    "entscheider_kein_interesse": "stat_bzh9jBOUMAJDN195VRrohErSuu6vTF4CofzipoOtOtF",
    "quali_terminiert_enes": "stat_c1U5gf7ObGY5VIvxchio6AFmtKvhdjst4lG3Bo3hxoU",
    "quali_terminiert_luk": "stat_6JP3mHvQnVmEUpOgdDcLy0YnB8ZN3ubqzFZSqRz3Mih",
    "quali_terminiert_sebastian": "stat_vKldwcyB9741E8NX3TA3qkRDJagRzFIOXLW3abkHW6v",
    "quali_terminiert_eren": "stat_jGwFvdSSBBZV2ljhIqht1ymA1lr0swoEKQJkUwMLTzW",
    "no_show_qc": "stat_2TXvU9dFI9aRV1GDcbGfsBVR1bZiImfzip3EakHDBTV",
    "sc_terminiert": "stat_s1QLeMGJ9CjlCSF9J9jmhkBFqPySFhsIhYM35rhh9Tp",
}

USERS = {
    "enes": {"id": "user_VphQt8gFT3hQbr9R52A51CQSA6eV6UeyKgnz3iCEZGe", "name": "Enes Erdogan", "termin_status": STATUS_CONFIG["quali_terminiert_enes"]},
    "luk": {"id": "user_7AYoeKx6OLtlpDYQC3EBPJRKUgFnXExtqEaLeSmXIuJ", "name": "Luk Gittner", "termin_status": STATUS_CONFIG["quali_terminiert_luk"]},
    "sebastian": {"id": "user_VdH6KwSarmfoVgEO2ZgchCf7mkyjK9mO6LPEVenllXb", "name": "Sebastian Sturm", "termin_status": STATUS_CONFIG["quali_terminiert_sebastian"]},
    "eren": {"id": "user_N3BaV6G9v63UVqOrVTiayOFrUfbC2E1SOmU5yPQOCSp", "name": "Eren Uzun", "termin_status": STATUS_CONFIG["quali_terminiert_eren"]},
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
        url = f"{BASE_URL}/{endpoint}"
        if params_tuple:
            params = dict(params_tuple)
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        
        req = urllib.request.Request(url, headers={"Authorization": _self.auth_header, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    def get_all_activities(self, date_from: str, date_to: str, activity_type: Optional[str] = None) -> List[Dict]:
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
        if not calls:
            return {
                "total_calls": 0, "connected_calls": 0, "total_duration": 0,
                "avg_duration": 0, "talk_time_min": 0, "connection_rate": 0,
            }
        
        total = len(calls)
        connected = [c for c in calls if c.get("status") == "completed" and c.get("duration", 0) > 0]
        durations = [c.get("duration", 0) or 0 for c in calls]
        connected_durations = [c.get("duration", 0) or 0 for c in connected]
        
        return {
            "total_calls": total,
            "connected_calls": len(connected),
            "total_duration": sum(durations),
            "avg_duration": round(sum(connected_durations) / len(connected), 1) if connected else 0,
            "talk_time_min": round(sum(durations) / 60, 1),
            "connection_rate": round(len(connected) / total * 100, 1) if total > 0 else 0,
        }
    
    def get_data_for_date(self, selected_date: date) -> Tuple[Dict, Dict, Dict]:
        date_str = selected_date.strftime("%Y-%m-%d")
        date_from = f"{date_str}T00:00:00"
        date_to = f"{date_str}T23:59:59"
        
        with st.spinner("Lade Status-Changes..."):
            status_changes = self.api.get_all_activities(date_from, date_to, "LeadStatusChange")
        
        with st.spinner("Lade Calls..."):
            all_activities = self.api.get_all_activities(date_from, date_to)
        
        calls = [a for a in all_activities if a.get("_type") == "Call"]
        
        # Calls nach User
        calls_by_user = defaultdict(list)
        for call in calls:
            uid = call.get("user_id")
            if uid:
                calls_by_user[uid].append(call)
        
        # Daten pro User
        user_data = {}
        team_success = {"qc_gefuehrt": 0, "no_shows": 0, "sc_terminiert": 0}
        
        for user_key, user_config in USERS.items():
            user_id = user_config["id"]
            user_calls = calls_by_user.get(user_id, [])
            call_metrics = self.calculate_call_metrics(user_calls)
            
            # Status Changes zählen
            sekr_erreicht = 0
            kein_interesse = 0
            termine = 0
            qc_gefuehrt = 0
            no_shows = 0
            sc_term = 0
            
            for activity in status_changes:
                if activity.get("user_id") != user_id:
                    continue
                
                new_status = activity.get("new_status_id")
                old_label = activity.get("old_status_label", "").lower()
                new_label = activity.get("new_status_label", "").lower()
                
                if new_status == STATUS_CONFIG["sekr_erreicht"]:
                    sekr_erreicht += 1
                elif new_status == STATUS_CONFIG["entscheider_kein_interesse"]:
                    kein_interesse += 1
                elif new_status == user_config["termin_status"]:
                    termine += 1
                elif new_status == STATUS_CONFIG["no_show_qc"]:
                    no_shows += 1
                elif new_status == STATUS_CONFIG["sc_terminiert"]:
                    sc_term += 1
                
                # QC geführt = Status-Change VON "Quali terminiert" ZU etwas anderem
                # (aber nicht zu einem anderen "Quali terminiert" Status)
                if "quali terminiert" in old_label and "quali terminiert" not in new_label:
                    qc_gefuehrt += 1
            
            # An VZ gescheitert = Verbunden - An Entscheider gescheitert
            sekr_erreicht = max(0, call_metrics["connected_calls"] - kein_interesse)
            
            # Entscheider erreicht = Verbunden - An VZ gescheitert
            entscheider_erreicht = max(0, call_metrics["connected_calls"] - sekr_erreicht)
            
            # Quoten berechnen
            total_calls = call_metrics["total_calls"]
            quotas = {
                "brutto_to_termin": round(termine / total_calls * 100, 1) if total_calls else 0,
                "brutto_connected": call_metrics["connection_rate"],
                "brutto_to_entscheider": round(entscheider_erreicht / total_calls * 100, 1) if total_calls else 0,
                "entscheider_to_termin": round(termine / entscheider_erreicht * 100, 1) if entscheider_erreicht else 0,
            }
            
            user_data[user_key] = {
                "name": user_config["name"],
                "calls": call_metrics,
                "termine": termine,
                "sekr_erreicht": sekr_erreicht,
                "kein_interesse": kein_interesse,
                "entscheider_erreicht": entscheider_erreicht,
                "quotas": quotas,
                # Erfolgsmetriken für separate Anzeige
                "qc_gefuehrt": qc_gefuehrt,
                "no_shows": no_shows,
                "sc_terminiert": sc_term,
            }
            
            # Team Erfolgsmetriken aggregieren
            team_success["qc_gefuehrt"] += qc_gefuehrt
            team_success["no_shows"] += no_shows
            team_success["sc_terminiert"] += sc_term
        
        # Team Gesamtwerte
        team_totals = {
            "total_calls": sum(u["calls"]["total_calls"] for u in user_data.values()),
            "total_connected": sum(u["calls"]["connected_calls"] for u in user_data.values()),
            "total_termine": sum(u["termine"] for u in user_data.values()),
            "total_talk_time": sum(u["calls"]["talk_time_min"] for u in user_data.values()),
            "total_sekr": sum(u["sekr_erreicht"] for u in user_data.values()),
            "total_kein_interesse": sum(u["kein_interesse"] for u in user_data.values()),
            **team_success
        }
        
        return user_data, team_totals, team_success


# ═════════════════════════════════════════════════════════════════════════════
# UI KOMPONENTEN
# ═════════════════════════════════════════════════════════════════════════════

def render_big_metric(label: str, value: str, delta: str = None, color: str = "primary"):
    """Große KPI-Metrik"""
    st.markdown(f"""
        <div style="
            background-color: {'#e8f4f8' if color == 'primary' else '#e8f8e8' if color == 'success' else '#fff4e6' if color == 'warning' else '#fde8e8'};
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid {COLORS[color]};
            margin-bottom: 10px;
        ">
            <div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 5px;">{label}</div>
            <div style="font-size: 32px; font-weight: bold; color: {COLORS[color] if color != 'primary' else COLORS['dark']};">{value}</div>
            {f'<div style="font-size: 12px; color: #27ae60;">{delta}</div>' if delta else ''}
        </div>
    """, unsafe_allow_html=True)


def render_user_card_compact(user_key: str, data: Dict):
    """Kompakte User-Card mit nur den wichtigsten Daten"""
    
    with st.container():
        st.markdown(f"### {data['name']}")
        
        # ERSTE REIHE: Calls und Termine
        cols = st.columns([1, 1, 1, 1, 1.5])
        
        with cols[0]:
            st.metric("📞 Anwahlen", data["calls"]["total_calls"])
        with cols[1]:
            st.metric("✅ Verbunden", f"{data['calls']['connected_calls']}")
        with cols[2]:
            st.metric("🎯 Termine", data["termine"], 
                     delta=f"{data['quotas']['brutto_to_termin']}%" if data["termine"] > 0 else None)
        with cols[3]:
            st.metric("⏱️ Ø Dauer", f"{data['calls']['avg_duration']}s")
        with cols[4]:
            st.metric("☎️ Anrufe/Termin", 
                     round(data["calls"]["total_calls"] / data["termine"], 1) if data["termine"] > 0 else "-",
                     help="Wie viele Anrufe waren nötig für einen Termin")
        
        # ZWEITE REIHE: Gescheitert (untergeordnet)
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        cols2 = st.columns([1, 1, 2])
        
        with cols2[0]:
            st.caption("An VZ gescheitert:")
            st.markdown(f"**{data['sekr_erreicht']}** (Sekr. erreicht)")
        with cols2[1]:
            st.caption("An Entscheider gescheitert:")
            st.markdown(f"**{data['kein_interesse']}** (Kein Interesse)")
        with cols2[2]:
            st.caption("Quote: Entscheider erreicht → Termin:")
            st.markdown(f"**{data['quotas']['entscheider_to_termin']}%**")
        
        st.markdown("<hr style='margin: 20px 0; border: none; border-top: 1px solid #eee;'>", unsafe_allow_html=True)


def render_success_bubble(team_success: Dict):
    """Übergeordnete Bubble mit Erfolgsmetriken"""
    
    st.markdown("## 📊 ÜBERGEBORDNETE METRIKEN")
    st.caption("Erfolgskontrolle & Funnel-Endstufen")
    
    cols = st.columns(3)
    
    with cols[0]:
        render_big_metric(
            "📋 QC Geführt", 
            str(team_success["qc_gefuehrt"]),
            color="info"
        )
    
    with cols[1]:
        render_big_metric(
            "🏃 No Shows", 
            str(team_success["no_shows"]),
            color="warning"
        )
    
    with cols[2]:
        render_big_metric(
            "📞 SC Terminiert", 
            str(team_success["sc_terminiert"]),
            color="success"
        )
    
    # Zusatzinfo
    if team_success["qc_gefuehrt"] > 0:
        no_show_rate = round(team_success["no_shows"] / team_success["qc_gefuehrt"] * 100, 1)
        st.info(f"📊 No-Show-Rate: {no_show_rate}% der geführten QCs sind nicht erschienen")


def render_team_overview_clean(team_totals: Dict):
    """Bereinigte Team-Übersicht ohne Erfolgsmetriken"""
    
    st.markdown("## 📈 TEAM GESAMT")
    
    # HIGHLIGHT: Termine groß anzeigen
    cols = st.columns([2, 1, 1, 1, 1])
    
    with cols[0]:
        render_big_metric(
            "🎯 TEAM TERMINE", 
            str(team_totals["total_termine"]),
            color="success"
        )
    with cols[1]:
        st.metric("Anwahlen", team_totals["total_calls"])
    with cols[2]:
        st.metric("Verbunden", team_totals["total_connected"])
    with cols[3]:
        st.metric("Sprechzeit", f"{team_totals['total_talk_time']}min")
    with cols[4]:
        quote = round(team_totals["total_termine"] / team_totals["total_calls"] * 100, 1) if team_totals["total_calls"] else 0
        st.metric("Quote", f"{quote}%", help="Bruttoanrufe zu Termin")
    
    # Sekundäre Metriken
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    cols2 = st.columns(2)
    
    with cols2[0]:
        st.caption("An VZ gescheitert (Sekr. erreicht):")
        st.markdown(f"**{team_totals['total_sekr']}**")
    
    with cols2[1]:
        st.caption("An Entscheider gescheitert (Kein Interesse):")
        st.markdown(f"**{team_totals['total_kein_interesse']}**")


# ═════════════════════════════════════════════════════════════════════════════
# HAUPTANWENDUNG
# ═════════════════════════════════════════════════════════════════════════════

def get_api_key():
    try:
        return st.secrets["close_api_key"]
    except:
        return st.sidebar.text_input("Close API Key", type="password", placeholder="api_...")


def main():
    st.sidebar.title("🦞 Close CRM Dashboard")
    st.sidebar.markdown("---")
    
    api_key = get_api_key()
    if not api_key:
        st.sidebar.warning("⚠️ Bitte API Key eingeben")
        st.stop()
    
    selected_date = st.sidebar.date_input("📅 Datum auswählen", value=date.today(), max_value=date.today())
    refresh = st.sidebar.button("🔄 Aktualisieren")
    
    st.title(f"Vertriebler Performance - {selected_date.strftime('%d.%m.%Y')}")
    
    api = CloseAPI(api_key)
    dashboard = DashboardData(api)
    
    cache_key = f"{selected_date}_{refresh}"
    if cache_key not in st.session_state or refresh:
        user_data, team_totals, team_success = dashboard.get_data_for_date(selected_date)
        st.session_state.update({
            "user_data": user_data,
            "team_totals": team_totals,
            "team_success": team_success,
            "cache_key": cache_key
        })
    else:
        user_data = st.session_state["user_data"]
        team_totals = st.session_state["team_totals"]
        team_success = st.session_state["team_success"]
    
    # ═════════════════════════════════════════════════════════════════
    # 1. TEAM GESAMT (fokussiert)
    # ═════════════════════════════════════════════════════════════════
    render_team_overview_clean(team_totals)
    
    st.markdown("---")
    
    # ═════════════════════════════════════════════════════════════════
    # 2. EINZELREPORTING (pro Person)
    # ═════════════════════════════════════════════════════════════════
    st.markdown("## 👤 EINZELREPORTING")
    
    for user_key, data in user_data.items():
        render_user_card_compact(user_key, data)
    
    st.markdown("---")
    
    # ═════════════════════════════════════════════════════════════════
    # 3. ÜBERGEORDNETE METRIKEN (Erfolgskontrolle)
    # ═════════════════════════════════════════════════════════════════
    render_success_bubble(team_success)
    
    # ═════════════════════════════════════════════════════════════════
    # 4. EXPORT
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
                "Termine": data["termine"],
                "Quote_Brutto_Termin": data["quotas"]["brutto_to_termin"],
                "Quote_Entscheider_Termin": data["quotas"]["entscheider_to_termin"],
                "Anrufe_pro_Termin": round(data["calls"]["total_calls"] / data["termine"], 1) if data["termine"] else 0,
                "QC_gefuehrt": data["qc_gefuehrt"],
                "No_Shows": data["no_shows"],
                "SC_terminiert": data["sc_terminiert"],
            })
        
        df = pd.DataFrame(df_data)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ CSV herunterladen", csv, f"close_report_{selected_date}.csv", "text/csv")


if __name__ == "__main__":
    main()
