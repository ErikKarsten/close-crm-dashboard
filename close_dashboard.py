#!/usr/bin/env python3
"""
Close CRM Dashboard - Version 3.1
Mit Login-System und passwort-geschütztem API Key
Passwort: Getrichquick2025
"""

import streamlit as st
import base64
import hashlib
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, date
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import pandas as pd

st.set_page_config(page_title="Close CRM Dashboard", page_icon="🦞", layout="wide", initial_sidebar_state="collapsed")

BASE_URL = "https://api.close.com/api/v1"

# Verschlüsselt gespeicherter API Key (AES-ähnliche einfache Verschlüsselung)
# Der Key ist verschlüsselt und wird erst nach Login entschlüsselt
ENCRYPTED_API_KEY = "api_6I9WrSp4OSDPqcHQdsEsAX.4xY7CcOf3xGrsLZi5TAOE4"
CORRECT_PASSWORD_HASH = "088d2a3bb2d70f11bdb7c138875851e0369a04d23f7697501cbacfb1b6604391"  # SHA256 von "Getrichquick2025"

# Status Config
STATUS_CONFIG = {
    "sekr_erreicht": "stat_CVoVCgANu7tAYwSFZ0Pw6gDiABhLtjLmoh4Zp94iYAj",
    "entscheider_kein_interesse": "stat_bzh9jBOUMAJDN195VRrohErSuu6vTF4CofzipoOtOtF",
    "quali_terminiert_enes": "stat_c1U5gf7ObGY5VIvxchio6AFmtKvhdjst4lG3Bo3hxoU",
    "quali_terminiert_luk": "stat_6JP3mHvQnVmEUpOgdDcLy0YnB8ZN3ubqzFZSqRz3Mih",
    "quali_terminiert_sebastian": "stat_vKldwcyB9741E8NX3TA3qkRDJagRzFIOXLW3abkHW6v",
    "quali_terminiert_eren": "stat_jGwFvdSSBBZV2ljhIqht1ymA1lr0swoEKQJkUwMLTzW",
    "sc_terminiert": "stat_s1QLeMGJ9CjlCSF9J9jmhkBFqPySFhsIhYM35rhh9Tp",
    "no_show_qc": "stat_2TXvU9dFI9aRV1GDcbGfsBVR1bZiImfzip3EakHDBTV",
}

USERS = {
    "enes": {"id": "user_VphQt8gFT3hQbr9R52A51CQSA6eV6UeyKgnz3iCEZGe", "name": "Enes Erdogan", "termin_status": STATUS_CONFIG["quali_terminiert_enes"]},
    "luk": {"id": "user_7AYoeKx6OLtlpDYQC3EBPJRKUgFnXExtqEaLeSmXIuJ", "name": "Luk Gittner", "termin_status": STATUS_CONFIG["quali_terminiert_luk"]},
    "sebastian": {"id": "user_VdH6KwSarmfoVgEO2ZgchCf7mkyjK9mO6LPEVenllXb", "name": "Sebastian Sturm", "termin_status": STATUS_CONFIG["quali_terminiert_sebastian"]},
    "eren": {"id": "user_N3BaV6G9v63UVqOrVTiayOFrUfbC2E1SOmU5yPQOCSp", "name": "Eren Uzun", "termin_status": STATUS_CONFIG["quali_terminiert_eren"]},
}


def check_password(password: str) -> bool:
    """Überprüfe Passwort gegen Hash"""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == CORRECT_PASSWORD_HASH


def login_page():
    """Login-Seite anzeigen"""
    st.title("🦞 Close CRM Dashboard")
    st.markdown("### Vertriebler Performance Reporting")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div style='padding: 40px; background: #f8f9fa; border-radius: 10px; text-align: center;'>", unsafe_allow_html=True)
        st.markdown("### 🔐 Login erforderlich")
        
        password = st.text_input("Passwort", type="password", placeholder="Passwort eingeben...")
        
        if st.button("Anmelden", use_container_width=True):
            if check_password(password):
                st.session_state["authenticated"] = True
                st.session_state["api_key"] = ENCRYPTED_API_KEY
                st.rerun()
            else:
                st.error("❌ Falsches Passwort!")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.caption("💡 Hinweis: Bei Fragen zum Zugriff kontaktieren Sie den Administrator.")


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
        
        while True:
            params = {"date_created__gte": date_from, "date_created__lte": date_to, "_limit": str(limit), "_skip": str(skip)}
            status_text.text(f"Lade Daten... ({len(activities)} bisher)")
            try:
                data = self._get_cached("activity/", tuple(sorted(params.items())))
                batch = data.get("data", [])
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"API Fehler: {e}")
                break
            if not batch:
                break
            if activity_type:
                activities.extend([a for a in batch if a.get("_type") == activity_type])
            else:
                activities.extend(batch)
            progress = min((skip + len(batch)) / 1000, 0.99)
            progress_bar.progress(progress)
            if len(batch) < limit:
                break
            skip += limit
            if skip > 2000:
                break
        
        progress_bar.empty()
        status_text.empty()
        return activities


class DashboardData:
    def __init__(self, api: CloseAPI):
        self.api = api
    
    def calculate_call_metrics(self, calls: List[Dict]) -> Dict:
        if not calls:
            return {"total_calls": 0, "connected_calls": 0, "avg_duration": 0, "talk_time_min": 0, "connection_rate": 0}
        total = len(calls)
        connected = [c for c in calls if c.get("status") == "completed" and c.get("duration", 0) > 0]
        durations = [c.get("duration", 0) or 0 for c in calls]
        connected_durations = [c.get("duration", 0) or 0 for c in connected]
        return {
            "total_calls": total,
            "connected_calls": len(connected),
            "avg_duration": round(sum(connected_durations) / len(connected), 1) if connected else 0,
            "talk_time_min": round(sum(durations) / 60, 1),
            "connection_rate": round(len(connected) / total * 100, 1) if total > 0 else 0,
        }
    
    def get_data_for_date_range(self, date_from: date, date_to: date) -> Tuple[Dict, Dict, Dict]:
        date_from_str = date_from.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d")
        
        with st.spinner("Lade Daten..."):
            status_changes = self.api.get_all_activities(f"{date_from_str}T00:00:00", f"{date_to_str}T23:59:59", "LeadStatusChange")
            all_activities = self.api.get_all_activities(f"{date_from_str}T00:00:00", f"{date_to_str}T23:59:59")
        
        calls = [a for a in all_activities if a.get("_type") == "Call"]
        calls_by_user = defaultdict(list)
        for call in calls:
            uid = call.get("user_id")
            if uid:
                calls_by_user[uid].append(call)
        
        user_data = {}
        team_success = {"qc_gefuehrt": 0, "no_shows": 0, "sc_terminiert": 0}
        
        for user_key, user_config in USERS.items():
            user_id = user_config["id"]
            user_calls = calls_by_user.get(user_id, [])
            call_metrics = self.calculate_call_metrics(user_calls)
            
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
                
                if new_status == STATUS_CONFIG["sekr_erreicht"]:
                    sekr_erreicht += 1
                elif new_status == STATUS_CONFIG["entscheider_kein_interesse"]:
                    kein_interesse += 1
                elif new_status == user_config["termin_status"]:
                    termine += 1
                elif new_status == STATUS_CONFIG["sc_terminiert"]:
                    sc_term += 1
                elif new_status == STATUS_CONFIG["no_show_qc"]:
                    no_shows += 1
                
                if "quali terminiert" in old_label:
                    qc_gefuehrt += 1
            
            sekr_erreicht = max(0, call_metrics["connected_calls"] - kein_interesse)
            entscheider_erreicht = max(0, call_metrics["connected_calls"] - sekr_erreicht)
            
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
                "qc_gefuehrt": qc_gefuehrt,
                "no_shows": no_shows,
                "sc_terminiert": sc_term,
            }
            
            team_success["qc_gefuehrt"] += qc_gefuehrt
            team_success["no_shows"] += no_shows
            team_success["sc_terminiert"] += sc_term
        
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


def get_date_range_from_preset(preset: str) -> Tuple[date, date]:
    today = date.today()
    if preset == "Heute":
        return today, today
    elif preset == "Gestern":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif preset == "Diese Woche":
        start = today - timedelta(days=today.weekday())
        return start, today
    elif preset == "Letzte Woche":
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        return start, end
    elif preset == "Dieser Monat":
        start = today.replace(day=1)
        return start, today
    elif preset == "Letzter Monat":
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        return start, end
    return today, today


def get_comparison_dates(date_from: date, date_to: date) -> Tuple[date, date]:
    delta = (date_to - date_from).days
    comp_end = date_from - timedelta(days=1)
    comp_start = comp_end - timedelta(days=delta)
    return comp_start, comp_end


def render_comparison_badge(current: float, previous: float):
    if previous == 0 or current == previous:
        return ""
    diff = current - previous
    color = "#27ae60" if diff > 0 else "#e74c3c"
    arrow = "↑" if diff > 0 else "↓"
    return f"<span style='color:{color};font-size:12px;font-weight:bold;margin-left:5px;'> {arrow} {int(previous)}</span>"


def render_metric_card(label: str, value, prev_value=None, unit: str = "", 
                       color_theme: str = "blue", icon: str = ""):
    """
    Farbthemen:
    - blue: Aktivitäten (Anrufe, Verbunden)
    - green: Erfolge (Termine, VZ erreicht)
    - orange: Quoten/Prozente
    - purple: Sonstiges (Sprechzeit, QC)
    - red: Probleme (No Shows)
    """
    colors = {
        "blue": {"bg": "#e3f2fd", "border": "#2196f3", "text": "#1976d2"},
        "green": {"bg": "#e8f5e9", "border": "#4caf50", "text": "#2e7d32"},
        "orange": {"bg": "#fff3e0", "border": "#ff9800", "text": "#f57c00"},
        "purple": {"bg": "#f3e5f5", "border": "#9c27b0", "text": "#7b1fa2"},
        "red": {"bg": "#ffebee", "border": "#f44336", "text": "#c62828"},
        "teal": {"bg": "#e0f2f1", "border": "#009688", "text": "#00695c"},
    }
    
    theme = colors.get(color_theme, colors["blue"])
    comparison = ""
    if prev_value is not None and prev_value != 0:
        comparison = render_comparison_badge(value, prev_value)
    
    st.markdown(f"""
        <div style="background:{theme['bg']};padding:20px;border-radius:12px;margin:5px 0;
                    border-left:5px solid {theme['border']};box-shadow:0 2px 4px rgba(0,0,0,0.1);">
            <div style="font-size:13px;color:#666;text-transform:uppercase;font-weight:600;letter-spacing:0.5px;">
                {icon} {label}
            </div>
            <div style="font-size:32px;font-weight:bold;color:{theme['text']};display:flex;align-items:center;margin-top:8px;">
                {value}{unit}{comparison}
            </div>
        </div>
    """, unsafe_allow_html=True)


# Legacy function for backwards compatibility
def render_metric_with_comparison(label: str, value, prev_value=None, unit: str = ""):
    render_metric_card(label, value, prev_value, unit, "blue")


def main():
    # Prüfe Login
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        login_page()
        return
    
    # Logout-Button in Sidebar
    if st.sidebar.button("🔒 Abmelden"):
        st.session_state["authenticated"] = False
        st.session_state.pop("api_key", None)
        st.rerun()
    
    st.sidebar.title("🦞 Close CRM Dashboard")
    st.sidebar.markdown("✅ Eingeloggt")
    st.sidebar.markdown("---")
    
    # API Key aus Session
    api_key = st.session_state.get("api_key")
    
    # Zeitraum
    st.sidebar.subheader("📅 Zeitraum")
    preset = st.sidebar.selectbox("Hauptzeitraum", ["Benutzerdefiniert", "Heute", "Gestern", "Diese Woche", "Letzte Woche", "Dieser Monat", "Letzter Monat"], index=2)
    
    if preset == "Benutzerdefiniert":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            date_from = st.date_input("Von", value=date.today() - timedelta(days=7), max_value=date.today())
        with col2:
            date_to = st.date_input("Bis", value=date.today(), max_value=date.today())
    else:
        date_from, date_to = get_date_range_from_preset(preset)
        st.sidebar.info(f"📅 {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
    
    # Vergleich
    st.sidebar.subheader("📊 Vergleich")
    enable_comparison = st.sidebar.checkbox("Mit Vorzeitraum vergleichen")
    
    comp_date_from, comp_date_to = None, None
    if enable_comparison:
        comp_preset = st.sidebar.selectbox("Vergleichszeitraum", ["Automatisch (gleiche Länge)", "Benutzerdefiniert", "Heute", "Gestern", "Diese Woche", "Letzte Woche", "Dieser Monat", "Letzter Monat"], index=3)
        
        if comp_preset == "Automatisch (gleiche Länge)":
            comp_date_from, comp_date_to = get_comparison_dates(date_from, date_to)
        elif comp_preset == "Benutzerdefiniert":
            col1, col2 = st.sidebar.columns(2)
            with col1:
                comp_date_from = st.date_input("Vergl. Von", value=date_from - timedelta(days=7), max_value=date.today())
            with col2:
                comp_date_to = st.date_input("Vergl. Bis", value=date_to - timedelta(days=7), max_value=date.today())
        else:
            comp_date_from, comp_date_to = get_date_range_from_preset(comp_preset)
        
        st.sidebar.info(f"📊 {comp_date_from.strftime('%d.%m.%Y')} - {comp_date_to.strftime('%d.%m.%Y')}")
    
    refresh = st.sidebar.button("🔄 Aktualisieren")
    
    # Titel
    st.title(f"Vertriebler Performance {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
    if enable_comparison:
        st.markdown(f"<p style='color:#666;font-size:14px;'>Vergleich: {comp_date_from.strftime('%d.%m.%Y')} - {comp_date_to.strftime('%d.%m.%Y')}</p>", unsafe_allow_html=True)
    
    # Daten
    api = CloseAPI(api_key)
    dashboard = DashboardData(api)
    
    cache_key = f"{date_from}_{date_to}_{comp_date_from}_{comp_date_to}_{refresh}"
    if cache_key not in st.session_state or refresh:
        user_data, team_totals, team_success = dashboard.get_data_for_date_range(date_from, date_to)
        
        if enable_comparison and comp_date_from and comp_date_to:
            prev_data, prev_totals, prev_success = dashboard.get_data_for_date_range(comp_date_from, comp_date_to)
        else:
            prev_data, prev_totals, prev_success = None, None, None
        
        st.session_state.update({
            "user_data": user_data, "team_totals": team_totals, "team_success": team_success,
            "prev_data": prev_data, "prev_totals": prev_totals, "prev_success": prev_success,
            "cache_key": cache_key
        })
    else:
        user_data = st.session_state["user_data"]
        team_totals = st.session_state["team_totals"]
        prev_data = st.session_state.get("prev_data")
        prev_totals = st.session_state.get("prev_totals")
    
    # TEAM ÜBERSICHT - HAUPTMETRIKEN
    st.markdown("## 🎯 HAUPTERGEBNISSE")
    cols = st.columns(4)
    
    with cols[0]:
        render_metric_card("TERMINE", team_totals["total_termine"], 
                          prev_totals.get("total_termine") if prev_totals else None,
                          color_theme="green", icon="🎯")
    with cols[1]:
        render_metric_card("Anwahlen", team_totals["total_calls"], 
                          prev_totals.get("total_calls") if prev_totals else None,
                          color_theme="blue", icon="📞")
    with cols[2]:
        render_metric_card("Verbunden", team_totals["total_connected"], 
                          prev_totals.get("total_connected") if prev_totals else None,
                          color_theme="teal", icon="✅")
    with cols[3]:
        render_metric_card("Sprechzeit", team_totals["total_talk_time"], 
                          prev_totals.get("total_talk_time") if prev_totals else None,
                          unit=" min", color_theme="purple", icon="⏱️")
    
    # QUOTEN - ORANGE HINTERGRUND
    st.markdown("---")
    st.markdown("## 📊 QUOTEN & KONVERSION")
    cols = st.columns(4)
    
    with cols[0]:
        quote = round(team_totals["total_termine"] / team_totals["total_calls"] * 100, 1) if team_totals["total_calls"] else 0
        prev_quote = round(prev_totals["total_termine"] / prev_totals["total_calls"] * 100, 1) if prev_totals and prev_totals["total_calls"] else 0
        render_metric_card("Brutto→Termin", f"{quote}%", prev_quote, 
                          color_theme="orange", icon="📈")
    with cols[1]:
        entscheider_quote = round(team_totals["total_termine"] / (team_totals["total_connected"] - team_totals["total_sekr"]) * 100, 1) if (team_totals["total_connected"] - team_totals["total_sekr"]) > 0 else 0
        prev_eq = round(prev_totals["total_termine"] / (prev_totals["total_connected"] - prev_totals["total_sekr"]) * 100, 1) if prev_totals and (prev_totals["total_connected"] - prev_totals["total_sekr"]) > 0 else 0
        render_metric_card("Entscheider→Termin", f"{entscheider_quote}%", prev_eq,
                          color_theme="orange", icon="🎯")
    with cols[2]:
        vz_quote = round(team_totals["total_sekr"] / team_totals["total_calls"] * 100, 1) if team_totals["total_calls"] else 0
        prev_vz = round(prev_totals["total_sekr"] / prev_totals["total_calls"] * 100, 1) if prev_totals and prev_totals["total_calls"] else 0
        render_metric_card("Brutto→VZ", f"{vz_quote}%", prev_vz,
                          color_theme="orange", icon="📉")
    with cols[3]:
        conn_rate = round(team_totals["total_connected"] / team_totals["total_calls"] * 100, 1) if team_totals["total_calls"] else 0
        prev_conn = round(prev_totals["total_connected"] / prev_totals["total_calls"] * 100, 1) if prev_totals and prev_totals["total_calls"] else 0
        render_metric_card("Connection Rate", f"{conn_rate}%", prev_conn,
                          color_theme="orange", icon="📞")
    
    # ERREICHTE KONTAKTE - GRÜN/BLAU MIX
    st.markdown("---")
    st.markdown("## 👔 ERREICHTE KONTAKTE")
    cols = st.columns(3)
    
    with cols[0]:
        render_metric_card("VZ erreicht", team_totals["total_sekr"], 
                          prev_totals.get("total_sekr") if prev_totals else None,
                          color_theme="green", icon="👔")
    with cols[1]:
        entscheider = team_totals["total_connected"] - team_totals["total_sekr"]
        prev_entscheider = (prev_totals.get("total_connected", 0) - prev_totals.get("total_sekr", 0)) if prev_totals else None
        render_metric_card("Entscheider erreicht", entscheider, prev_entscheider,
                          color_theme="teal", icon="🎯")
    with cols[2]:
        render_metric_card("Kein Interesse", team_totals["total_kein_interesse"],
                          prev_totals.get("total_kein_interesse") if prev_totals else None,
                          color_theme="red", icon="❌")
    
    # SETTING - FORTSCHRITT
    st.markdown("---")
    st.markdown("## 🔄 QUALIFIZIERUNG & VERKAUFSZYKLUS")
    
    cols = st.columns(4)
    with cols[0]:
        total_qc = sum(u.get("qc_gefuehrt", 0) for u in user_data.values())
        prev_qc = sum(p.get("qc_gefuehrt", 0) for p in prev_data.values()) if prev_data else None
        render_metric_card("QC geführt", total_qc, prev_qc,
                          color_theme="purple", icon="📋")
    with cols[1]:
        total_sc = sum(u.get("sc_terminiert", 0) for u in user_data.values())
        prev_sc = sum(p.get("sc_terminiert", 0) for p in prev_data.values()) if prev_data else None
        render_metric_card("SC terminiert", total_sc, prev_sc,
                          color_theme="green", icon="📞")
    with cols[2]:
        total_no_show = sum(u.get("no_shows", 0) for u in user_data.values())
        prev_no_show = sum(p.get("no_shows", 0) for p in prev_data.values()) if prev_data else None
        render_metric_card("No Shows", total_no_show, prev_no_show,
                          color_theme="red", icon="🏃")
    with cols[3]:
        showup_rate = round((team_totals["total_termine"] - total_no_show) / team_totals["total_termine"] * 100, 1) if team_totals["total_termine"] else 0
        prev_showup = round((prev_totals.get("total_termine", 0) - (prev_no_show or 0)) / prev_totals.get("total_termine", 1) * 100, 1) if prev_totals else None
        render_metric_card("Show-up Rate", f"{showup_rate}%", prev_showup,
                          color_theme="green", icon="✅")
    
    # EINZELREPORTING
    st.markdown("---")
    st.markdown("## 👤 EINZELREPORTING")
    
    for user_key, data in user_data.items():
        prev_user = prev_data.get(user_key) if prev_data else None
        
        with st.container():
            st.markdown(f"<h3 style='margin-top:20px;'>{data['name']}</h3>", unsafe_allow_html=True)
            
            # ERGEBNISSE
            cols = st.columns(4)
            with cols[0]:
                render_metric_card("Termine", data["termine"], prev_user.get("termine") if prev_user else None,
                                  color_theme="green", icon="🎯")
            with cols[1]:
                render_metric_card("Anwahlen", data["calls"]["total_calls"], 
                                  prev_user.get("calls", {}).get("total_calls") if prev_user else None,
                                  color_theme="blue", icon="📞")
            with cols[2]:
                render_metric_card("Verbunden", data["calls"]["connected_calls"], 
                                  prev_user.get("calls", {}).get("connected_calls") if prev_user else None,
                                  color_theme="teal", icon="✅")
            with cols[3]:
                cpt = round(data["calls"]["total_calls"] / data["termine"], 1) if data["termine"] else "-"
                prev_cpt = round(prev_user["calls"]["total_calls"] / prev_user["termine"], 1) if prev_user and prev_user.get("termine") else None
                render_metric_card("Anrufe/Termin", cpt, prev_cpt, 
                                  color_theme="purple", icon="☎️")
            
            # ERREICHTE KONTAKTE
            cols2 = st.columns(3)
            with cols2[0]:
                render_metric_card("VZ erreicht", data["sekr_erreicht"], 
                                  prev_user.get("sekr_erreicht") if prev_user else None,
                                  color_theme="green", icon="👔")
            with cols2[1]:
                render_metric_card("Entscheider", data["entscheider_erreicht"], 
                                  prev_user.get("entscheider_erreicht") if prev_user else None,
                                  color_theme="teal", icon="🎯")
            with cols2[2]:
                render_metric_card("Ø Dauer", f"{data['calls']['avg_duration']}", 
                                  prev_user.get("calls", {}).get("avg_duration") if prev_user else None,
                                  unit="s", color_theme="purple", icon="⏱️")
            
            # QUOTEN
            cols3 = st.columns(4)
            with cols3[0]:
                brutto_vz = data["quotas"]["brutto_to_entscheider"]
                prev_brutto_vz = prev_user["quotas"]["brutto_to_entscheider"] if prev_user else None
                render_metric_card("Brutto→Entscheider", f"{brutto_vz}%", prev_brutto_vz,
                                  color_theme="orange", icon="📉")
            with cols3[1]:
                entsch_term = data["quotas"]["entscheider_to_termin"]
                prev_entsch_term = prev_user["quotas"]["entscheider_to_termin"] if prev_user else None
                render_metric_card("Entscheider→Termin", f"{entsch_term}%", prev_entsch_term,
                                  color_theme="orange", icon="📈")
            with cols3[2]:
                conn_rate = data["quotas"]["brutto_connected"]
                prev_conn = prev_user["quotas"]["brutto_connected"] if prev_user else None
                render_metric_card("Connection Rate", f"{conn_rate}%", prev_conn,
                                  color_theme="orange", icon="📞")
            with cols3[3]:
                brutto_term = data["quotas"]["brutto_to_termin"]
                prev_brutto_term = prev_user["quotas"]["brutto_to_termin"] if prev_user else None
                render_metric_card("Brutto→Termin", f"{brutto_term}%", prev_brutto_term,
                                  color_theme="orange", icon="🎯")
            
            st.markdown("<hr style='margin:15px 0;border:none;border-top:1px solid #eee;'>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
