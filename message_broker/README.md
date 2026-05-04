# Pub/Sub Message Broker (FastAPI + WebSockets)

## 📌 Popis projektu

Tato aplikace implementuje jednoduchý **Message Broker** pomocí FastAPI a WebSocketů.

Broker umožňuje komunikaci mezi klienty pomocí návrhového vzoru **Publish/Subscribe (Pub/Sub)**:

* Klienti se mohou přihlásit k odběru tématu (subscribe)
* Klienti mohou posílat zprávy do tématu (publish)
* Broker automaticky doručí zprávy všem přihlášeným odběratelům

---

## ⚙️ Použité technologie

* Python
* FastAPI
* WebSockets
* asyncio (asynchronní programování)
* JSON
* MessagePack (binární formát)

---

## 🧱 Struktura projektu

* `main.py` – WebSocket server (broker)
* `manager.py` – správa připojených klientů a topiců
* `client.py` – testovací klient (publisher / subscriber)

---

## ▶️ Spuštění projektu

### 1. Aktivace virtuálního prostředí

```bash
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 2. Instalace závislostí

```bash
pip install fastapi uvicorn websockets msgpack
```

### 3. Spuštění serveru

```bash
uvicorn main:app --reload
```

---

## 🧪 Použití klienta

Spusť klienta:

```bash
python client.py
```

Zvol režim:

```
mode (sub/pub): sub
```

Zvol formát:

```
format (json/msgpack): json
```

---

## 🔄 Formát zpráv

Zprávy mají strukturu:

```json
{
  "action": "publish",
  "topic": "news",
  "payload": "Ahoj"
}
```

---

## 📡 Endpoint

WebSocket endpoint:

```
ws://127.0.0.1:8000/broker
```

---

## 🧠 Funkcionalita

* více klientů současně
* topics (subscribe / publish)
* broadcast zpráv
* podpora JSON i MessagePack

---

## 👥 Poznámka

Projekt byl rozdělen na dvě části:

* Implementace brokeru a klienta (tato část)
* Další rozšíření (benchmark, testy, persistence)
