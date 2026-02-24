#!/usr/bin/env python3
"""
Close CRM Live Dashboard
Streamlit-App für Echtzeit-Vertriebler-Performance

Start:
  export CLOSE_API_KEY="api_..."
  streamlit run close_dashboard_v2.py
"""

import streamlit as st
import base64
import json
import urllib.request
import urllib.parse
import os
from datetime import datetime, date
from collections import defaultdict
from typing import Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ═════════════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Close CRM Dashboard",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_URL = "https://api.close.com/api/v1"

TERMINATION_STATUSES = {
    "enes": "stat_c1U5gf7ObGY5VIvxchio6AFmtKvhdjst4lG3Bo3hxoU",
    "luk": "stat_6JP3mHvQnVmEUpOgdDcLy0YnB8ZN3ubqzFZSqRz3Mih",
    "sebastian": "stat_vKldwcyB9741E8NX3TA3qkRDJagRzFIOXLW3abkHW6v",
}

USERS = {
    "enes": "user_VphQt8gFT3hQbr9R52A51CQSA6eV6UeyKgnz3iCEZGe",
    "sebastian": "user_VdH6KwSarmfoVgEO2ZgchCf7mkyjK9mO6LPEVenllXb",
    "luk": "user_7AYoeKx6OLtlpDYQC3EBPJRKUgFnXExtqEaLeSmXIuJ",
}

USER_NAMES = {
    "enes": "Enes Erdogan",
    "sebastian": "Sebastian Sturm",
    "luk": "Luk Gittner",
}


# ═════════════════════════════════════════════════════════════════════════════
# API KLASSE
# ═════════════════════════════════════════════════════════════════════════════

class CloseAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        auth_str = base64.b64encode(f"{api_key}:".encode()).decode()
        self.auth_header = f"Basic {auth_str}"

    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """API Request mit Error Handling"""
        url = f"{BASE_URL}/{endpoint}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": self.auth_header,
                "Content-Type": "application/json"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise Exception("❌ API-Key ungültig. Bitte überprüfen.")
            elif e.code == 429:
                raise Exception("❌ Rate limit erreicht. Bitte warten.")
            else:
                raise Exception(f"❌ API Fehler: HTTP {e.code}")
        except Exception as e:
            raise Exception(f"❌ Verbindungsfehler: {e}")

    def get_all_activities(self, date_from: str, date_to: str, 
                          activity_type: Optional[str] = None) -> List[Dict]:
        """Fetch alle Activities mit Pagination"""
        activities = []
        skip = 0
        limit = 100
        max_iterations = 50
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        iterations = 0
        while iterations < max_iterations:
            params = {
                "date_created__gte": date_from,
                "date_created__lte": date_to,
                "_limit": str(limit),
                "_skip": str(skip),
            }
            
            status_text.text(f"Lade Daten... ({len(activities)} bisher)")
            
            try:
                data = self._make_request("activity/", params)
                batch = data.get("data", [])
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(str(e))
                return []
            
            if not batch:
                break
            
            if activity_type:
                filtered = [a for a in batch if a.get("_type") == activity_type]
                activities.extend(filtered)
            else:
                activities.extend(batch)
            
            progress = min((skip + len(batch)) / 1000, 0.99)
            progress_bar.progress(progress)
            
            if len(batch) < limit:
                break
            
            skip += limit
            iterations += 1
        
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
                "total_duration_seconds": 0, "avg_duration_seconds": 0,
                "avg_duration_connected": 0, "total_talk_time_minutes": 0,
                "connection_rate_percent": 0,
            }
        
        total = len(calls)
        connected = [c for c in calls if c.get("status") == "completed" and c.get("duration", 0) > 0]
        failed = [c for c in calls if c.get("status") in ["failed", "no-answer", "busy"]]
        
        durations = [c.get("duration", 0) or 0 for c in calls]
        connected_durations = [c.get("duration", 0) or 0 for c in connected]
        
        total_duration = sum(durations)
        avg_duration = total_duration / total if total > 0 else 0
        avg_connected = sum(connected_durations) / len(connected) if connected else 0
        
        return {
            "total_calls": total,
            "connected_calls": len(connected),
            "failed_calls": len(failed),
            "total_duration_seconds": total_duration,
            "avg_duration_seconds": round(avg_duration, 1),
            "avg_duration_connected": round(avg_connected, 1),
            "total_talk_time_minutes": round(total_duration / 60, 1),
            "connection_rate_percent": round(len(connected) / total * 100, 1) if total > 0 else 0,
        }
    
    def get_data_for_date(self, selected_date: date) -> Dict:
        """Hole alle Daten für ein Datum"""
        date_str = selected_date.strftime("%Y-%m-%d")
        date_from = f"{date_str}T00:00:00"
        date_to = f"{date_str}T23:59:59"
        
        # Status Changes (Terminierungen)
        with st.spinner("Lade Terminierungen..."):
            status_changes = self.api.get_all_activities(date_from, date_to, "LeadStatusChange")
        
        # Alle Calls
        with st.spinner("Lade Anrufe..."):
            all_activities = self.api.get_all_activities(date_from, date_to)
        
        calls = [a for a in all_activities if a.get("_type") == "Call"]
        
        # Nach User gruppieren
        calls_by_user = defaultdict(list)
        for call in calls:
            user_id = call.get("user_id")
            if user_id:
                calls_by_user[user_id].append(call)
        
        # Terminierungen zählen
        terminations = defaultdict(int)
        for activity in status_changes:
            user_id = activity.get("user_id")
            status_id = activity.get("new_status_id")
            
            for name, uid in USERS.items():
                if user_id == uid and status_id in TERMINATION_STATUSES.values():
                    terminations[name] += 1
        
        # Metriken pro User
        user_data = {}
        for name, user_id in USERS.items():
            user_calls = calls_by_user.get(user_id, [])
            call_metrics = self.calculate_call_metrics(user_calls)
            
            user_data[name] = {
                "name": USER_NAMES[name],
                "calls": call_metrics,
                "terminations": terminations[name],
                "calls_per_termination": round(call_metrics["total_calls"] / terminations[name], 1) if terminations[name] > 0 else 0,
            }
        
        return user_data


# ═════════════════════════════════════════════════════════════════════════════
# UI KOMPONENTEN
# ═════════════════════════════════════════════════════════════════════════════

def create_comparison_chart(user_data: Dict):
    """Erstelle Vergleichs-Chart"""
    df_data = []
    for name, data in user_data.items():
        df_data.append({
            "Vertriebler": data["name"],
            "Anrufe": data["calls"]["total_calls"],
            "Verbunden": data["calls"]["connected_calls"],
            "Termine": data["terminations"],
            "Verbindungsrate": data["calls"]["connection_rate_percent"],
        })
    
    df = pd.DataFrame(df_data)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Anrufe & Termine", "Verbindungsrate %"),
        specs=[[{"secondary_y": True}, {}]]
    )
    
    fig.add_trace(
        go.Bar(name="Anrufe", x=df["Vertriebler"], y=df["Anrufe"], marker_color="#1f77b4"),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(name="Termine", x=df["Vertriebler"], y=df["Termine"], marker_color="#ff7f0e"),
        row=1, col=1, secondary_y=True
    )
    
    fig.add_trace(
        go.Bar(name="Verbindungsrate %", x=df["Vertriebler"], y=df["Verbindungsrate"], marker_color="#2ca02c"),
        row=1, col=2
    )
    
    fig.update_layout(
        height=400,
        showlegend=True,
        title_text="Team-Vergleich",
        barmode="group"
    )
    
    return fig


def render_user_section(name: str, data: Dict):
    """Render Abschnitt für einen Vertriebler"""
    calls = data["calls"]
    
    with st.expander(f"👤 {data['name']}", expanded=True):
        cols = st.columns(4)
        
        with cols[0]:
            st.metric("📞 Anrufe", calls["total_calls"])
        with cols[1]:
            st.metric("✅ Verbunden", f"{calls['connected_calls']} ({calls['connection_rate_percent']}%)")
        with cols[2]:
            st.metric("⏱️ Ø Dauer", f"{calls['avg_duration_connected']}s")
        with cols[3]:
            st.metric("🎯 Termine", data["terminations"])
        
        detail_cols = st.columns(3)
        with detail_cols[0]:
            st.caption("**Sprechzeit**")
            st.write(f"{calls['total_talk_time_minutes']} Minuten")
        with detail_cols[1]:
            st.caption("**Fehlgeschlagen**")
            st.write(f"{calls['failed_calls']} Anrufe")
        with detail_cols[2]:
            st.caption("**Effizienz**")
            st.write(f"{data['calls_per_termination']} Anrufe/Termin")


# ═════════════════════════════════════════════════════════════════════════════
# HAUPTANWENDUNG
# ═════════════════════════════════════════════════════════════════════════════

def main():
    # Sidebar
    st.sidebar.title("🦞 Close CRM Dashboard")
    st.sidebar.markdown("---")
    
    # API Key laden
    api_key = None
    
    # 1. Versuche aus Environment Variable
    env_key = os.environ.get("CLOSE_API_KEY")
    if env_key:
        api_key = env_key.strip()
    
    # 2. Versuche aus Streamlit Secrets
    if not api_key:
        try:
            api_key = st.secrets.get("close_api_key")
        except:
            pass
    
    # 3. Manuelle Eingabe falls kein Key gefunden
    if not api_key:
        api_key = st.sidebar.text_input(
            "Close API Key", 
            type="password",
            placeholder="api_...",
            help="Dein Close CRM API Key"
        )
    else:
        # Zeige Maskierung wenn Key automatisch geladen wurde
        masked = api_key[:8] + "..." + api_key[-4:]
        st.sidebar.success(f"✅ API-Key geladen: {masked}")
    
    if not api_key:
        st.sidebar.warning("⚠️ Bitte API Key eingeben")
        st.info("💡 Tipp: Setze den API-Key als Environment Variable:\n\n`export CLOSE_API_KEY=api_...`")
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
    try:
        if refresh or "user_data" not in st.session_state or st.session_state.get("last_date") != selected_date:
            user_data = dashboard.get_data_for_date(selected_date)
            st.session_state["user_data"] = user_data
            st.session_state["last_date"] = selected_date
        else:
            user_data = st.session_state["user_data"]
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return
    
    if not user_data:
        st.warning("⚠️ Keine Daten gefunden für dieses Datum")
        return
    
    # Team-Übersicht
    st.subheader("📈 Team-Übersicht")
    
    total_calls = sum(d["calls"]["total_calls"] for d in user_data.values())
    total_connected = sum(d["calls"]["connected_calls"] for d in user_data.values())
    total_terminations = sum(d["terminations"] for d in user_data.values())
    total_talk_time = sum(d["calls"]["total_talk_time_minutes"] for d in user_data.values())
    
    overview_cols = st.columns(4)
    with overview_cols[0]:
        st.metric("📞 Team-Anrufe", total_calls)
    with overview_cols[1]:
        st.metric("✅ Verbunden", total_connected)
    with overview_cols[2]:
        st.metric("🎯 Termine", total_terminations)
    with overview_cols[3]:
        st.metric("⏱️ Sprechzeit", f"{total_talk_time} Min")
    
    # Vergleichs-Chart
    st.plotly_chart(create_comparison_chart(user_data), use_container_width=True)
    
    # Einzelne Vertriebler
    st.markdown("---")
    st.subheader("👤 Einzelübersichten")
    
    for name, data in user_data.items():
        render_user_section(name, data)
    
    # Export
    st.markdown("---")
    if st.button("📥 CSV Export"):
        df_data = []
        for name, data in user_data.items():
            calls = data["calls"]
            df_data.append({
                "Name": data["name"],
                "Datum": selected_date,
                "Anrufe": calls["total_calls"],
                "Verbunden": calls["connected_calls"],
                "Verbindungsrate": calls["connection_rate_percent"],
                "Ø Dauer": calls["avg_duration_connected"],
                "Sprechzeit": calls["total_talk_time_minutes"],
                "Termine": data["terminations"],
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
