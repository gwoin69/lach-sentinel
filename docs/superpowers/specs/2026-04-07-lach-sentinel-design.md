# lach-sentinel — Design Spec
**Date :** 2026-04-07  
**Statut :** Approuvé

---

## 1. Objectif

`lach-sentinel` est une application de monitoring et de découverte réseau pour serveur Unraid, packagée en un seul conteneur Docker. Elle remplit deux fonctions principales de poids égal :

1. **Monitoring Unraid** — supervision en temps réel du serveur, de ses conteneurs Docker et de ses VMs
2. **Découverte réseau** — scans Nmap planifiés, enrichissement d'une base d'hôtes, gestion via interface web

L'authentification et les notifications sont explicitement hors scope pour la v1 mais les interfaces sont prévues pour les brancher proprement en v2.

---

## 2. Architecture

### Vue d'ensemble

Un seul conteneur Docker contenant :

```
lach-sentinel/
├── backend/          # FastAPI (Python 3.12)
│   ├── api/          # Routes REST /api/v1/…
│   ├── ws/           # WebSocket /ws
│   ├── modules/
│   │   ├── unraid_monitor.py   # Collecte métriques Unraid
│   │   ├── nmap_scanner.py     # Scans réseau
│   │   ├── retention.py        # Downsampling SQLite
│   │   └── alert_engine.py     # Stub v2
│   └── scheduler.py            # APScheduler
├── frontend/         # Vue.js 3 (Vite)
│   └── dist/         # Assets statiques servis par FastAPI
└── data/
    └── sentinel.db   # SQLite
```

### Flux de données

```
Unraid API (7443) ──► Unraid Monitor (60s) ──► SQLite metrics
Réseau local      ──► Nmap Scanner (réglable) ──► SQLite hosts/scan_results
APScheduler       ──► Downsampling auto ──────► SQLite metrics_hourly / metrics_daily
SQLite            ──► FastAPI REST + WebSocket ──► Vue.js SPA (push 5s)
```

---

## 3. Modules backend

### 3.1 Unraid Monitor

Interroge l'API Unraid locale toutes les **60 secondes** (configurable via `METRICS_INTERVAL`).

Données collectées :
- Système : CPU (usage %), RAM (utilisée/totale), températures (CPU + disques), uptime
- Stockage : array (utilisé/total, état), cache (utilisé/total), parité (dernier check, état), disques individuels (température, état SMART)
- Conteneurs Docker : liste, état (running/stopped/paused), CPU %, RAM utilisée
- VMs : liste, état (running/stopped/paused), vCPU, RAM allouée

### 3.2 Nmap Scanner

Scans planifiés sur la plage `NMAP_RANGE` à la fréquence `NMAP_INTERVAL`.

Informations collectées par hôte :
- IP, hostname (reverse DNS)
- MAC address + vendor lookup
- OS fingerprinting (`-O`)
- Ports ouverts + services + versions (`-sV`)
- NSE scripts configurables depuis l'UI

Comportement :
- Si un hôte est découvert pour la première fois → insertion en base avec statut `new`
- Si un hôte connu ne répond plus → marqué `absent` (non supprimé)
- Si un hôte absent revient → marqué `returned`
- Les hôtes sont éditables manuellement (nom, tags, notes, monitoring on/off)

### 3.3 Stratégie de rétention SQLite

Job APScheduler déclenché toutes les heures :

| Table | Résolution | Durée de rétention |
|---|---|---|
| `metrics` | 1 min (brut) | 7 jours |
| `metrics_hourly` | 1 heure (agrégat) | 3 mois |
| `metrics_daily` | 1 jour (agrégat) | 1 an |

Volume estimé : < 500 MB pour 1 an complet.

### 3.4 Alert Engine (stub v2)

Module présent mais inactif en v1. Interface définie :
```python
async def send_alert(level: str, message: str, context: dict) -> None:
    pass  # v2 : Telegram, Email, Webhook
```

---

## 4. API REST

Base path : `/api/v1/`

| Endpoint | Méthode | Description |
|---|---|---|
| `/metrics/current` | GET | Métriques Unraid en temps réel |
| `/metrics/history` | GET | Historique (params: `from`, `to`, `resolution`) |
| `/containers` | GET | Liste des conteneurs |
| `/vms` | GET | Liste des VMs |
| `/hosts` | GET/POST | Liste/création d'hôtes |
| `/hosts/{id}` | GET/PUT/DELETE | Détail/édition/suppression d'un hôte |
| `/hosts/{id}/services` | GET/POST | Services associés à un hôte |
| `/scans` | GET | Historique des scans Nmap |
| `/scans/trigger` | POST | Déclencher un scan manuel |
| `/config` | GET/PUT | Configuration globale (plage, intervalles…) |

### WebSocket

`/ws` — push toutes les `WS_PUSH_INTERVAL` secondes (défaut : 5s) :
```json
{ "type": "metrics_update", "data": { "cpu": 23, "ram_used": 14.2, ... }, "timestamp": "..." }
{ "type": "host_new",       "data": { "ip": "192.168.111.42", "vendor": "Apple" }, "timestamp": "..." }
{ "type": "host_absent",    "data": { "ip": "192.168.111.10", "label": "NAS" }, "timestamp": "..." }
```

---

## 5. Schéma de base de données SQLite

```sql
-- Métriques brutes (TTL 7j)
CREATE TABLE metrics (
  id INTEGER PRIMARY KEY,
  timestamp DATETIME NOT NULL,
  type TEXT NOT NULL,      -- 'cpu', 'ram', 'temp_cpu', 'disk_*', etc.
  value REAL NOT NULL,
  meta TEXT                -- JSON pour données structurées (conteneurs, disques)
);
CREATE INDEX idx_metrics_ts ON metrics(timestamp);
CREATE INDEX idx_metrics_type_ts ON metrics(type, timestamp);

-- Agrégats horaires (TTL 3 mois)
CREATE TABLE metrics_hourly (
  id INTEGER PRIMARY KEY,
  hour DATETIME NOT NULL,
  type TEXT NOT NULL,
  avg REAL, min REAL, max REAL
);

-- Agrégats journaliers (TTL 1 an)
CREATE TABLE metrics_daily (
  id INTEGER PRIMARY KEY,
  day DATE NOT NULL,
  type TEXT NOT NULL,
  avg REAL, min REAL, max REAL
);

-- Hôtes réseau
CREATE TABLE hosts (
  id INTEGER PRIMARY KEY,
  ip TEXT NOT NULL UNIQUE,
  hostname TEXT,
  mac TEXT,
  vendor TEXT,
  os TEXT,
  status TEXT DEFAULT 'active',  -- active, absent, returned
  label TEXT,                    -- nom personnalisé
  notes TEXT,
  tags TEXT,                     -- JSON array
  monitoring_enabled INTEGER DEFAULT 1,
  first_seen DATETIME NOT NULL,
  last_seen DATETIME NOT NULL
);

-- Services par hôte
CREATE TABLE services (
  id INTEGER PRIMARY KEY,
  host_id INTEGER REFERENCES hosts(id),
  port INTEGER NOT NULL,
  protocol TEXT NOT NULL,
  service_name TEXT,
  version TEXT,
  state TEXT,
  last_seen DATETIME
);

-- Résultats de scans
CREATE TABLE scan_results (
  id INTEGER PRIMARY KEY,
  started_at DATETIME NOT NULL,
  finished_at DATETIME,
  range TEXT NOT NULL,
  hosts_found INTEGER,
  status TEXT,   -- running, completed, failed
  raw_output TEXT
);

-- Configuration
CREATE TABLE config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

---

## 6. Frontend Vue.js

### Stack
- Vue 3 + Vite + TypeScript
- Pinia (state management)
- Vue Router
- Chart.js ou uPlot (graphiques métriques)
- WebSocket natif pour les mises à jour temps réel

### Pages / sections (sidebar)

| Route | Contenu |
|---|---|
| `/` | Dashboard — KPIs + widgets masquables |
| `/unraid` | Détail système Unraid (disques, températures…) |
| `/containers` | Liste complète des conteneurs + stats |
| `/vms` | Liste des VMs + état |
| `/network` | Carte réseau + résumé dernier scan |
| `/hosts` | Table des hôtes avec édition inline |
| `/scans` | Historique + déclenchement manuel |
| `/settings` | Config plage, intervalles, connexion Unraid |

### Dashboard widgets masquables
Chaque widget est togglable depuis le bouton ⚙ Widgets :
- KPIs système (CPU, RAM, Temp, Uptime)
- Stockage (array, cache, parité)
- Conteneurs Docker
- Machines virtuelles
- Résumé réseau

Préférences stockées dans `localStorage`.

---

## 7. Conteneur Docker

### Dockerfile (multi-stage)

```dockerfile
# Stage 1 : build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2 : image finale
FROM python:3.12-slim
RUN apt-get update && apt-get install -y nmap && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
VOLUME ["/data"]
EXPOSE 8888
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8888"]
```

### Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `UNRAID_HOST` | `192.168.111.253` | IP du serveur Unraid |
| `UNRAID_API_PORT` | `7443` | Port API Unraid |
| `UNRAID_API_KEY` | *(requis)* | Clé API Unraid |
| `NMAP_RANGE` | `192.168.111.0/24` | Plage de scan |
| `NMAP_INTERVAL` | `3600` | Fréquence scan (secondes) |
| `METRICS_INTERVAL` | `60` | Fréquence collecte métriques (secondes) |
| `WS_PUSH_INTERVAL` | `5` | Fréquence push WebSocket (secondes) |
| `TZ` | `Europe/Paris` | Fuseau horaire |

### Volumes
- `/data` → SQLite + config persistante

### Capabilities Docker requises
```yaml
cap_add:
  - NET_ADMIN
  - NET_RAW
```
Nécessaires pour les scans Nmap avec détection OS et MAC.

### Template Unraid (Community Applications)
- Port exposé : `8888` (mappé vers port hôte configurable)
- `--network=bridge` par défaut, `--network=host` optionnel pour Nmap
- Variables pré-remplies avec les valeurs par défaut ci-dessus

---

## 8. Gestion des erreurs

| Scénario | Comportement |
|---|---|
| API Unraid inaccessible | Log d'erreur, dernier état connu conservé, dashboard affiche "Données indisponibles" |
| Scan Nmap échoue | Scan marqué `failed` en base, retry au prochain intervalle |
| SQLite corrompu | Log critique, application stoppe (pas de corruption silencieuse) |
| WebSocket déconnecté | Reconnexion automatique côté Vue.js avec backoff exponentiel |

---

## 9. Hors scope (v1)

- Authentification / gestion d'utilisateurs
- Notifications (Telegram, Email, Discord, Webhook)
- Support multi-serveurs Unraid
- Graphiques de topologie réseau avancés
- Alertes configurables (seuils CPU, RAM, etc.)
- Import/export de la base d'hôtes
