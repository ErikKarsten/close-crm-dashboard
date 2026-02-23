#!/bin/bash
# Setup-Skript für Close CRM Dashboard
# Dieses Skript richtet das GitHub Repository ein

echo "🦞 Close CRM Dashboard - GitHub Setup"
echo "===================================="
echo ""

# Prüfen ob git installiert ist
if ! command -v git &> /dev/null; then
    echo "❌ Git ist nicht installiert. Bitte installieren:"
    echo "   https://git-scm.com/downloads"
    exit 1
fi

# GitHub Token abfragen
echo "🔑 Du benötigst einen GitHub Personal Access Token."
echo "   Erstelle einen hier: https://github.com/settings/tokens"
echo "   (Berechtigungen: 'repo' auswählen)"
echo ""
read -s -p "GitHub Token eingeben: " GITHUB_TOKEN
echo ""

# Repository Name
echo ""
read -p "Repository Name [close-crm-dashboard]: " REPO_NAME
REPO_NAME=${REPO_NAME:-close-crm-dashboard}

read -p "GitHub Username: " GITHUB_USER

if [ -z "$GITHUB_USER" ] || [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Username und Token werden benötigt!"
    exit 1
fi

# Repository erstellen via API
echo ""
echo "📁 Erstelle Repository auf GitHub..."
curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/user/repos \
    -d "{\"name\":\"$REPO_NAME\",\"private\":false}" > /tmp/github_response.json

if [ $? -eq 0 ]; then
    echo "✅ Repository erstellt: https://github.com/$GITHUB_USER/$REPO_NAME"
else
    echo "⚠️ Repository existiert möglicherweise bereits oder Fehler aufgetreten"
fi

# Git initialisieren und pushen
echo ""
echo "📤 Lade Dateien hoch..."

# Ins Verzeichnis wechseln (angenommen Skript ist im gleichen Ordner wie die Dateien)
cd "$(dirname "$0")"

git init
git add .
git commit -m "Initial commit: Close CRM Dashboard"
git branch -M main
git remote add origin "https://$GITHUB_USER:$GITHUB_TOKEN@github.com/$GITHUB_USER/$REPO_NAME.git"
git push -u origin main

echo ""
echo "✅ Fertig! Dein Dashboard ist jetzt auf GitHub:"
echo "   https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo "🚀 Nächster Schritt: Deployment auf Streamlit Cloud"
echo "   1. Gehe zu: https://share.streamlit.io"
echo "   2. Verbinde dein GitHub Konto"
echo "   3. Wähle das Repository aus"
echo "   4. Füge den Close API Key in den Secrets hinzu"
echo ""
