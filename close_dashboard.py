#!/usr/bin/env python3
"""
Close CRM Dashboard - Version 4.0
Modernes, klares UI mit Visualisierungen
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
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Close CRM Dashboard", page_icon="🦞", layout="wide")

BASE_URL = "https://api.close.com/api/v1"

ENCRYPTED_API_KEY = "api_6I9WrSp4OSDPqcHQdsEsAX.4xY7CcOf3xGrsLZi5TAOE4"
CORRECT_PASSWORD_HASH = "088d2a3bb2d70f11bdb7c138875851e0369a04d23f7697501cbacfb1b6604391"

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
    "enes": {"id": "user_VphQt8gFT3hQbr9R52A51CQSA6eV6UeyKgnz3iCEZGe", "name": "Enes Erdogan", "termin_status": STATUS_CONFIG["quali_terminiert_enes"], "color": "#3498db"},
    "luk": {"id": "user_7AYoeKx6OLtlpDYQC3EBPJRKUgFnXExtqEaLeSmXIuJ", "name": "Luk Gittner", "termin_status": STATUS_CONFIG["quali_terminiert_luk"], "color": "#e74c3c"},
    "sebastian": {"id": "user_VdH6KwSarmfoVgEO2ZgchCf7mkyjK9mO6LPEVenllXb", "name": "Sebastian Sturm", "termin_status": STATUS_CONFIG["quali_terminiert_sebastian"], "color": "#2ecc71"},
    "eren": {"id": "user_N3BaV6G9v63UVqOrVTiayOFrUfbC2E1SOmU5yPQOCSp", "name": "Eren Uzun", "termin_status": STATUS_CONFIG["quali_terminiert_eren"], "color": "#9b59b6"},
}


def check_password(password: str) -> bool:
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == CORRECT_PASSWORD_HASH


def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align:center;padding:60px 40px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:20px;color:white;'>", unsafe_allow_html=True)
        st.markdown("<h1>🦞 Close CRM</h1>", unsafe_allow_html=True)
        st.markdown("<h3>Vertriebler Dashboard</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        password = st.text_input("Passwort", type="password", placeholder="••••••••")
        
        if st.button("Anmelden", use_container_width=True):
            if check_password(password):
                st.session_state["authenticated"] = True
                st.session_state["api_key"] = ENCRYPTED_API_KEY
                st.rerun()
            else:
                st.error("❌ Falsches Passwort")
        
        st.markdown("</div>", unsafe_allow_html=True)


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
        progress_bar = st.progress(0, text="Lade Daten...")
        
        while True:
            params = {"date_created__gte": date_from, "date_created__lte": date_to, "_limit": str(limit), "_skip": str(skip)}
            try:
                data = self._get_cached("activity/", tuple(sorted(params.items())))
                batch = data.get("data", [])
            except Exception as e:
                progress_bar.empty()
                st.error(f"API Fehler: {e}")
                break
            if not batch:
                break
            if activity_type:
                activities.extend([a for a in batch if a.get("_type") == activity_type])
            else:
                activities.extend(batch)
            progress = min((skip + len(batch)) / 1000, 0.99)
            progress_bar.progress(progress, text=f"Lade Daten... ({len(activities)} geladen)")
            if len(batch) < limit:
                break
            skip += limit
            if skip > 2000:
                break
        
        progress_bar.empty()
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
    
    def get_data_for_date_range(self, date_from: date, date_to: date) -> Tuple[Dict, Dict]:
        date_from_str = date_from.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d")
        
        with st.spinner(""):
            status_changes = self.api.get_all_activities(f"{date_from_str}T00:00:00", f"{date_to_str}T23:59:59", "LeadStatusChange")
            all_activities = self.api.get_all_activities(f"{date_from_str}T00:00:00", f"{date_to_str}T23:59:59")
        
        calls = [a for a in all_activities if a.get("_type") == "Call"]
        calls_by_user = defaultdict(list)
        for call in calls:
            uid = call.get("user_id")
            if uid:
                calls_by_user[uid].append(call)
        
        user_data = {}
        
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
            
            user_data[user_key] = {
                "name": user_config["name"],
                "color": user_config["color"],
                "calls": call_metrics,
                "termine": termine,
                "sekr_erreicht": sekr_erreicht,
                "kein_interesse": kein_interesse,
                "entscheider_erreicht": entscheider_erreicht,
                "qc_gefuehrt": qc_gefuehrt,
                "no_shows": no_shows,
                "sc_terminiert": sc_term,
                # Quoten
                "brutto_to_termin": round(termine / total_calls * 100, 1) if total_calls else 0,
                "connection_rate": call_metrics["connection_rate"],
                "entscheider_to_termin": round(termine / entscheider_erreicht * 100, 1) if entscheider_erreicht else 0,
                "cpt": round(total_calls / termine, 1) if termine else 0,
            }
        
        team_totals = {
            "total_calls": sum(u["calls"]["total_calls"] for u in user_data.values()),
            "total_connected": sum(u["calls"]["connected_calls"] for u in user_data.values()),
            "total_termine": sum(u["termine"] for u in user_data.values()),
            "total_talk_time": sum(u["calls"]["talk_time_min"] for u in user_data.values()),
            "total_sekr": sum(u["sekr_erreicht"] for u in user_data.values()),
            "total_kein_interesse": sum(u["kein_interesse"] for u in user_data.values()),
            "qc_gefuehrt": sum(u["qc_gefuehrt"] for u in user_data.values()),
            "no_shows": sum(u["no_shows"] for u in user_data.values()),
            "sc_terminiert": sum(u["sc_terminiert"] for u in user_data.values()),
        }
        
        return user_data, team_totals


def create_comparison_chart(user_data: Dict):
    """Balkendiagramm für Anwahlen-Vergleich"""
    names = [u["name"].split()[0] for u in user_data.values()]  # Nur Vornamen
    calls = [u["calls"]["total_calls"] for u in user_data.values()]
    colors = [u["color"] for u in user_data.values()]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=names,
        y=calls,
        marker_color=colors,
        text=calls,
        textposition='outside',
        textfont=dict(size=16, color='white'),
        hovertemplate='<b>%{x}</b><br>Anwahlen: %{y}<extra></extra>',
    ))
    
    fig.update_layout(
        title=dict(text='📞 Anwahlen pro Vertriebler', font=dict(size=20, color='white'), x=0.5),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(title='', tickfont=dict(size=14)),
        yaxis=dict(title='Anzahl', gridcolor='rgba(255,255,255,0.1)', tickfont=dict(size=12)),
        showlegend=False,
        height=350,
        margin=dict(t=50, b=30, l=50, r=30),
    )
    
    return fig


def create_metrics_grid(team_totals: Dict):
    """Kompakte Metrik-Karten"""
    
    def metric_card(title, value, subtitle="", color="#3498db"):
        return f"""
        <div style="background:linear-gradient(135deg,{color}22 0%,{color}11 100%);border:1px solid {color}44;
                    border-radius:12px;padding:20px;text-align:center;margin:5px;">
            <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:1px;">{title}</div>
            <div style="font-size:36px;font-weight:bold;color:{color};margin:10px 0;">{value}</div>
            <div style="font-size:11px;color:#666;">{subtitle}</div>
        </div>
        """
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(metric_card("🎯 TERMINE", team_totals["total_termine"], 
                               f"{round(team_totals['total_termine']/team_totals['total_calls']*100,1)}% Quote" if team_totals['total_calls'] else "", 
                               "#27ae60"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("📞 ANWAHLEN", team_totals["total_calls"], 
                               f"{team_totals['total_connected']} verbunden", 
                               "#3498db"), unsafe_allow_html=True)
    with col3:
        conn_rate = round(team_totals["total_connected"]/team_totals["total_calls"]*100,1) if team_totals["total_calls"] else 0
        st.markdown(metric_card("📊 CONNECTION", f"{conn_rate}%", 
                               "Verbindungsrate", 
                               "#9b59b6"), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_card("⏱️ ZEIT", f"{team_totals['total_talk_time']}", 
                               "Gesamtminuten", 
                               "#e67e22"), unsafe_allow_html=True)


def create_user_cards(user_data: Dict):
    """Einzelne User-Karten"""
    for user_key, data in user_data.items():
        with st.container():
            # Header mit Name und Farbe
            st.markdown(f"""
                <div style="background:{data['color']}20;border-left:5px solid {data['color']};padding:15px 20px;margin:20px 0 10px 0;border-radius:0 10px 10px 0;">
                    <h2 style="color:{data['color']};margin:0;font-size:24px;">{data['name']}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            # Metriken in 4 Spalten
            m1, m2, m3, m4 = st.columns(4)
            
            with m1:
                st.metric("📞 Anwahlen", data["calls"]["total_calls"])
                st.caption(f"Ø {data['calls']['avg_duration']}s")
            with m2:
                st.metric("✅ Verbunden", data["calls"]["connected_calls"])
                st.caption(f"{data['calls']['connection_rate']}% Rate")
            with m3:
                st.metric("🎯 Termine", data["termine"])
                st.caption(f"☎️ {data['cpt']} Anrufe/Termin")
            with m4:
                entsch_quote = data["entscheider_to_termin"]
                st.metric("📈 Entscheider→Termin", f"{entsch_quote}%")
                st.caption(f"👔 {data['sekr_erreicht']} VZ erreicht")
            
            # Progress bars für Quoten
            st.progress(min(data["brutto_to_termin"] / 10, 1.0), 
                       text=f"Brutto→Termin: {data['brutto_to_termin']}%")
            
            st.markdown("---")


def get_date_range_from_preset(preset: str) -> Tuple[date, date]:
    today = date.today()
    if preset == "Heute":
        return today, today
    elif preset == "Gestern":
        return today - timedelta(days=1), today - timedelta(days=1)
    elif preset == "Diese Woche":
        return today - timedelta(days=today.weekday()), today
    elif preset == "Letzte Woche":
        end = today - timedelta(days=today.weekday() + 1)
        return end - timedelta(days=6), end
    elif preset == "Dieser Monat":
        return today.replace(day=1), today
    elif preset == "Letzter Monat":
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    return today, today


def main():
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        login_page()
        return
    
    # Sidebar
    with st.sidebar:
        if st.button("🔒 Abmelden"):
            st.session_state["authenticated"] = False
            st.rerun()
        
        st.title("⚙️ Einstellungen")
        preset = st.selectbox("Zeitraum", ["Heute", "Gestern", "Diese Woche", "Letzte Woche", "Dieser Monat", "Letzter Monat"], index=1)
        date_from, date_to = get_date_range_from_preset(preset)
        st.info(f"📅 {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
        refresh = st.button("🔄 Aktualisieren", use_container_width=True)
    
    # Header
    st.markdown(f"""
        <div style="background:linear-gradient(90deg,#1a1a2e 0%,#16213e 100%);padding:30px;border-radius:15px;margin-bottom:30px;">
            <h1 style="color:white;margin:0;">🦞 Close CRM Dashboard</h1>
            <p style="color:#888;margin:10px 0 0 0;">{date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Daten laden
    api = CloseAPI(st.session_state["api_key"])
    dashboard = DashboardData(api)
    
    cache_key = f"{date_from}_{date_to}_{refresh}"
    if cache_key not in st.session_state or refresh:
        user_data, team_totals = dashboard.get_data_for_date_range(date_from, date_to)
        st.session_state.update({"user_data": user_data, "team_totals": team_totals, "cache_key": cache_key})
    else:
        user_data = st.session_state["user_data"]
        team_totals = st.session_state["team_totals"]
    
    # TEAM ÜBERSICHT
    st.markdown("## 📊 Team Übersicht")
    create_metrics_grid(team_totals)
    
    # BALKENDIAGRAMM
    st.markdown("## 📈 Vergleich Anwahlen")
    st.plotly_chart(create_comparison_chart(user_data), use_container_width=True)
    
    # EINZELNE VERTRIEBLER
    st.markdown("## 👤 Einzelergebnisse")
    create_user_cards(user_data)
    
    # ZUSAMMENFASSUNG
    st.markdown("## 📝 Zusammenfassung")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ Erfolge**")
        st.markdown(f"- **{team_totals['total_termine']}** Termine insgesamt")
        st.markdown(f"- **{team_totals['sc_terminiert']}** SC terminiert")
        st.markdown(f"- **{team_totals['qc_gefuehrt']}** QC geführt")
    
    with col2:
        st.markdown("**⚠️ Herausforderungen**")
        showup = round((team_totals['total_termine'] - team_totals['no_shows']) / team_totals['total_termine'] * 100, 1) if team_totals['total_termine'] else 0
        st.markdown(f"- **{team_totals['no_shows']}** No Shows ({showup}% Show-up)")
        st.markdown(f"- **{team_totals['total_kein_interesse']}** Kein Interesse")
        st.markdown(f"- **{team_totals['total_sekr']}** VZ erreicht")


if __name__ == "__main__":
    main()
