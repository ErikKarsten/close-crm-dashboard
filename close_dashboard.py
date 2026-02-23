#!/usr/bin/env python3
"""
Close CRM Dashboard - Version 3.0
Mit flexibler Vergleichszeitraum-Auswahl und farbigen Vergleichsindikatoren
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

st.set_page_config(page_title="Close CRM Dashboard", page_icon="🦞", layout="wide")

BASE_URL = "https://api.close.com/api/v1"

# Status und User Config
STATUS_CONFIG = {
    "sekr_erreicht": "stat_CVoVCgANu7tAYwSFZ0Pw6gDiABhLtjLmoh4Zp94iYAj",
    "entscheider_kein_interesse": "stat_bzh9jBOUMAJDN195VRrohErSuu6vTF4CofzipoOtOtF",
    "quali_terminiert_enes": "stat_c1U5gf7ObGY5VIvxchio6AFmtKvhdjst4lG3Bo3hxoU",
    "quali_terminiert_luk": "stat_6JP3mHvQnVmEUpOgdDcLy0YnB8ZN3ubqzFZSqRz3Mih",
    "quali_terminiert_sebastian": "stat_vKldwcyB9741E8NX3TA3qkRDJagRzFIOXLW3abkHW6v",
    "quali_terminiert_eren": "stat_jGwFvdSSBBZV2ljhIqht1ymA1lr0swoEKQJkUwMLTzW",
    "sc_terminiert": "stat_s1QLeMGJ9CjlCSF9J9jmhkBFqPySFhsIhYM35rhh9Tp",
}

USERS = {
    "enes": {"id": "user_VphQt8gFT3hQbr9R52A51CQSA6eV6UeyKgnz3iCEZGe", "name": "Enes Erdogan", "termin_status": STATUS_CONFIG["quali_terminiert_enes"]},
    "luk": {"id": "user_7AYoeKx6OLtlpDYQC3EBPJRKUgFnXExtqEaLeSmXIuJ", "name": "Luk Gittner", "termin_status": STATUS_CONFIG["quali_terminiert_luk"]},
    "sebastian": {"id": "user_VdH6KwSarmfoVgEO2ZgchCf7mkyjK9mO6LPEVenllXb", "name": "Sebastian Sturm", "termin_status": STATUS_CONFIG["quali_terminiert_sebastian"]},
    "eren": {"id": "user_N3BaV6G9v63UVqOrVTiayOFrUfbC2E1SOmU5yPQOCSp", "name": "Eren Uzun", "termin_status": STATUS_CONFIG["quali_terminiert_eren"]},
}


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
        while True:
            params = {"date_created__gte": date_from, "date_created__lte": date_to, "_limit": str(limit), "_skip": str(skip)}
            try:
                data = self._get_cached("activity/", tuple(sorted(params.items())))
                batch = data.get("data", [])
            except:
                break
            if not batch:
                break
            if activity_type:
                activities.extend([a for a in batch if a.get("_type") == activity_type])
            else:
                activities.extend(batch)
            if len(batch) < limit:
                break
            skip += limit
            if skip > 2000:
                break
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
        date_from_api = f"{date_from_str}T00:00:00"
        date_to_api = f"{date_to_str}T23:59:59"
        
        status_changes = self.api.get_all_activities(date_from_api, date_to_api, "LeadStatusChange")
        all_activities = self.api.get_all_activities(date_from_api, date_to_api)
        
        calls = [a for a in all_activities if a.get("_type") == "Call"]
        calls_by_user = defaultdict(list)
        for call in calls:
            uid = call.get("user_id")
            if uid:
                calls_by_user[uid].append(call)
        
        user_data = {}
        team_success = {"qc_gefuehrt": 0, "sc_terminiert": 0}
        
        for user_key, user_config in USERS.items():
            user_id = user_config["id"]
            user_calls = calls_by_user.get(user_id, [])
            call_metrics = self.calculate_call_metrics(user_calls)
            
            sekr_erreicht = 0
            kein_interesse = 0
            termine = 0
            qc_gefuehrt = 0
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
                elif new_status == STATUS_CONFIG["sc_terminiert"]:
                    sc_term += 1
                
                if "quali terminiert" in old_label and "quali terminiert" not in new_label:
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
                "sc_terminiert": sc_term,
            }
            
            team_success["qc_gefuehrt"] += qc_gefuehrt
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
    """Render farbigen Vergleichsindikator"""
    if previous == 0 or current == previous:
        return ""
    diff = current - previous
    
    # Grün = besser (höher), Rot = schlechter (niedriger)
    color = "#27ae60" if diff > 0 else "#e74c3c"
    arrow = "↑" if diff > 0 else "↓"
    
    return f"<span style='color:{color};font-size:11px;font-weight:bold;margin-left:5px;'> {arrow} {int(previous)}</span>"


def render_metric_with_comparison(label: str, value, prev_value=None, unit: str = ""):
    """Render Metrik mit Vergleichs-Label"""
    comparison = ""
    if prev_value is not None and prev_value != 0:
        comparison = render_comparison_badge(value, prev_value)
    
    st.markdown(f"""
        <div style="background:#f8f9fa;padding:15px;border-radius:8px;margin:5px 0;border-left:3px solid #3498db;">
            <div style="font-size:12px;color:#666;text-transform:uppercase;">{label}</div>
            <div style="font-size:28px;font-weight:bold;color:#2c3e50;display:flex;align-items:center;">
                {value}{unit}{comparison}
            </div>
        </div>
    """, unsafe_allow_html=True)


def main():
    st.sidebar.title("🦞 Close CRM Dashboard")
    st.sidebar.markdown("---")
    
    try:
        api_key = st.secrets["close_api_key"]
    except:
        api_key = st.sidebar.text_input("Close API Key", type="password", placeholder="api_...")
    
    if not api_key:
        st.sidebar.warning("⚠️ Bitte API Key eingeben")
        st.stop()
    
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
    
    # Vergleichszeitraum - GENAUSO FLEXIBEL
    st.sidebar.subheader("📊 Vergleich")
    enable_comparison = st.sidebar.checkbox("Mit Vorzeitraum vergleichen")
    
    comp_date_from, comp_date_to = None, None
    if enable_comparison:
        comp_preset = st.sidebar.selectbox(
            "Vergleichszeitraum",
            ["Automatisch (gleiche Länge, davor)", "Benutzerdefiniert", "Heute", "Gestern", "Diese Woche", "Letzte Woche", "Dieser Monat", "Letzter Monat"],
            index=3
        )
        
        if comp_preset == "Automatisch (gleiche Länge, davor)":
            comp_date_from, comp_date_to = get_comparison_dates(date_from, date_to)
        elif comp_preset == "Benutzerdefiniert":
            col1, col2 = st.sidebar.columns(2)
            with col1:
                comp_date_from = st.date_input("Vergl. Von", value=date_from - timedelta(days=7), max_value=date.today())
            with col2:
                comp_date_to = st.date_input("Vergl. Bis", value=date_to - timedelta(days=7), max_value=date.today())
        else:
            comp_date_from, comp_date_to = get_date_range_from_preset(comp_preset)
        
        st.sidebar.info(f"📊 Vergleich: {comp_date_from.strftime('%d.%m.%Y')} - {comp_date_to.strftime('%d.%m.%Y')}")
    
    refresh = st.sidebar.button("🔄 Aktualisieren")
    
    # Titel
    st.title(f"Vertriebler Performance {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
    if enable_comparison:
        st.markdown(f"<p style='color:#666;font-size:14px;'>Vergleich mit: {comp_date_from.strftime('%d.%m.%Y')} - {comp_date_to.strftime('%d.%m.%Y')}</p>", unsafe_allow_html=True)
    
    # Daten laden
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
    
    # TEAM ÜBERSICHT
    st.markdown("## 📈 TEAM GESAMT")
    cols = st.columns(5)
    
    with cols[0]:
        prev_val = prev_totals.get("total_termine") if prev_totals else None
        render_metric_with_comparison("🎯 TERMINE", team_totals["total_termine"], prev_val)
    with cols[1]:
        prev_val = prev_totals.get("total_calls") if prev_totals else None
        render_metric_with_comparison("📞 Anwahlen", team_totals["total_calls"], prev_val)
    with cols[2]:
        prev_val = prev_totals.get("total_connected") if prev_totals else None
        render_metric_with_comparison("✅ Verbunden", team_totals["total_connected"], prev_val)
    with cols[3]:
        prev_val = prev_totals.get("total_talk_time") if prev_totals else None
        render_metric_with_comparison("⏱️ Sprechzeit", team_totals["total_talk_time"], prev_val, "min")
    with cols[4]:
        quote = round(team_totals["total_termine"] / team_totals["total_calls"] * 100, 1) if team_totals["total_calls"] else 0
        prev_quote = round(prev_totals["total_termine"] / prev_totals["total_calls"] * 100, 1) if prev_totals and prev_totals["total_calls"] else 0
        render_metric_with_comparison("📊 Quote", f"{quote}%", prev_quote)
    
    # EINZELREPORTING
    st.markdown("---")
    st.markdown("## 👤 EINZELREPORTING")
    
    for user_key, data in user_data.items():
        prev_user = prev_data.get(user_key) if prev_data else None
        
        with st.container():
            st.markdown(f"<h3 style='margin-top:20px;'>{data['name']}</h3>", unsafe_allow_html=True)
            
            cols = st.columns(5)
            with cols[0]:
                prev_val = prev_user.get("calls", {}).get("total_calls") if prev_user else None
                render_metric_with_comparison("📞 Anwahlen", data["calls"]["total_calls"], prev_val)
            with cols[1]:
                prev_val = prev_user.get("calls", {}).get("connected_calls") if prev_user else None
                render_metric_with_comparison("✅ Verbunden", data["calls"]["connected_calls"], prev_val)
            with cols[2]:
                prev_val = prev_user.get("termine") if prev_user else None
                render_metric_with_comparison("🎯 Termine", data["termine"], prev_val)
            with cols[3]:
                prev_val = prev_user.get("calls", {}).get("avg_duration") if prev_user else None
                render_metric_with_comparison("⏱️ Ø Dauer", f"{data['calls']['avg_duration']}", prev_val, "s")
            with cols[4]:
                cpt = round(data["calls"]["total_calls"] / data["termine"], 1) if data["termine"] else "-"
                prev_cpt = round(prev_user["calls"]["total_calls"] / prev_user["termine"], 1) if prev_user and prev_user.get("termine") else None
                render_metric_with_comparison("☎️ Anrufe/Termin", cpt, prev_cpt)
            
            st.markdown("<hr style='margin:15px 0;border:none;border-top:1px solid #eee;'>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
