Kroky pro správné spuštění:
1) spustit message_broker: message_broker/ uvicorn main:app --reload --port 8000

2) Hlavní appku zapnout přes: uvicorn main:app --reload --port 8000

3) Pak zapnout workera: py worker.py

Integrační test: test.py

bonus: test_flow - vytváří test_bucket ve kterém zkusí uploadnout test.png z hlavního adresáře do bucketu a na něm následně provést operaci