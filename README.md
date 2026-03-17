# XAU/USD Live Signal Dashboard

Dashboard temps réel pour recevoir les alertes patterns de TradingView via Webhook.

## Stack
- **Backend** : Flask + Flask-SocketIO (Python)
- **Frontend** : HTML/CSS/JS + Socket.IO
- **Hébergement** : Render.com (gratuit)
- **Source** : TradingView Webhook + Pine Script

---

## Déploiement sur Render (10 minutes)

### 1. Mettre le projet sur GitHub
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/TON-USER/xauusd-bot.git
git push -u origin main
```

### 2. Créer le service sur Render
1. Va sur https://render.com → New → Web Service
2. Connecte ton repo GitHub
3. Paramètres :
   - **Name** : xauusd-dashboard
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn --worker-class eventlet -w 1 app:app`
4. Clique **Deploy**
5. Attends 2-3 minutes → tu as une URL comme `https://xauusd-dashboard.onrender.com`

---

## Configuration TradingView

### Étape 1 : Ajouter le script Pine
1. Ouvre ton chart XAU/USD 5m sur TradingView
2. Éditeur Pine → colle le contenu de `tradingview_alert.pine`
3. Remplace `YOUR-APP` par ton URL Render
4. Clique **Enregistrer** puis **Ajouter à l'indicateur**

### Étape 2 : Créer l'alerte
1. Clic droit sur le chart → **Ajouter une alerte**
2. Condition : sélectionne ton indicateur
3. Dans **Notifications** → active **Webhook URL**
4. URL : `https://xauusd-dashboard.onrender.com/webhook`
5. Message : laisser vide (le Pine Script génère le JSON)
6. Clique **Créer**

---

## Format JSON envoyé par TradingView

```json
{
  "type": "pattern",
  "pattern": "Bullish Engulfing",
  "action": "BUY",
  "price": 5016.13,
  "sl": 5004.50,
  "tp": 5038.00,
  "rr": 2.1,
  "time": "2024-03-17T13:46:01Z"
}
```

---

## Test en local (optionnel)

```bash
pip install -r requirements.txt
python app.py
# Ouvre http://localhost:5000
```

Pour exposer en local avec ngrok :
```bash
ngrok http 5000
# Utilise l'URL ngrok dans TradingView
```

---

## Endpoints disponibles

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Status du serveur |
| `/webhook` | POST | Reçoit les alertes TradingView |
| `/signals` | GET | Liste des derniers signaux (JSON) |
| `/signals/clear` | POST | Efface les signaux |

---

## Fonctionnalités du dashboard

- Flux de signaux en temps réel (WebSocket)
- Badge BUY / SELL coloré
- Prix, SL, TP, R/R par signal
- Son d'alerte différencié (BUY = aigu, SELL = grave)
- Statistiques session (nb signaux, meilleur R/R, pattern fréquent)
- Niveaux S/R fixes XAU/USD
- Boutons test BUY/SELL intégrés
