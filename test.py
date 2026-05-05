import pytest
import asyncio
import json
import websockets

# conf
BROKER_URI = "ws://127.0.0.1:8001/broker"

TEST_FILE_ID = "6d1111eb-0155-4a54-a879-a73d4db95aef"
TEST_BUCKET_ID = "f6049dd3-877f-4a6e-968e-a840ad5a1e26"
TEST_USER_ID = "test-user"

@pytest.mark.asyncio
async def test_live_worker_10_jobs():
    print(f"\nPřipojuji se k brokeru na {BROKER_URI}...")
    
    async with websockets.connect(BROKER_URI) as ws:
        await ws.send(json.dumps({
            "action": "subscribe",
            "topic": "image.done"
        }))
        sub_resp = await ws.recv()
        print(f"Subscribed: {sub_resp}")

        # odeslání 10 tasků
        print(f"Odesílám 10 úloh pro soubor {TEST_FILE_ID}...")
        for i in range(10):
            job = {
                "action": "publish",
                "topic": "image.jobs",
                "payload": {
                    "operation": "invert",
                    "file_id": TEST_FILE_ID,
                    "bucket_id": TEST_BUCKET_ID,
                    "user_id": TEST_USER_ID
                }
            }
            await ws.send(json.dumps(job))

        # 10 confirmationů
        confirmations = []
        print("Čekám na potvrzení od workeru (timeout 20s)...")
        
        try:
            async with asyncio.timeout(20):
                while len(confirmations) < 10:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    
                    payload = data.get("payload", data)
                    
                    if payload.get("status") == "done":
                        confirmations.append(payload)
                        print(f"[{len(confirmations)}/10] Worker dokončil: {payload.get('file_id')}")
                    elif payload.get("status") == "error":
                        print(f"!! Worker vrátil chybu: {payload.get('error')}")
                        confirmations.append(payload)
        except asyncio.TimeoutError:
            print("Chyba: Čas vypršel, worker neodpověděl na všech 10 úloh.")

        done_count = len([c for c in confirmations if c.get("status") == "done"])
        print(f"\n--- VÝSLEDEK ---")
        print(f"Celkem přijato zpráv: {len(confirmations)}")
        print(f"Úspěšně zpracováno: {done_count}")
        
        assert done_count == 10, f"Očekávalo se 10 úspěšných zpracování, ale bylo jich {done_count}"

if __name__ == "__main__":
    pytest.main([__file__, "-s"])
