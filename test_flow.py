"""
Test complete flow: Upload -> Process -> Download
"""
import requests
import json
import time
import os

GATEWAY_URL = "http://localhost:8000"

def test_complete_flow():
    print("TEST: Complete Image Processing Flow\n")

    
    # 1. Create bucket
    print("Creating bucket...\n")
    bucket_resp = requests.post(f"{GATEWAY_URL}/buckets", json={"name": "test-bucket-1"})
    if bucket_resp.status_code != 200:
        print(f"Failed to create bucket: {bucket_resp.text}\n")
        return
    
    bucket_id = bucket_resp.json()["id"]
    print(f"Bucket created: {bucket_id}\n")
    
    # 2. Upload test image
    print("Uploading test image...\n")
    
    # Check if test.png exists
    if not os.path.exists("test.png"):
        print("test.png not found!\n")
        return
    
    with open("test.png", "rb") as f:
        files = {
            "file": ("test.png", f),
            "user_id": (None, "test-user"),
            "bucket_id": (None, bucket_id)
        }
        upload_resp = requests.post(f"{GATEWAY_URL}/files/upload", files=files)
    
    if upload_resp.status_code != 200:
        print(f"Failed to upload: {upload_resp.text}\n")
        return
    
    file_id = upload_resp.json()["id"]
    print(f"Image uploaded: {file_id}\n")
    
    # 3. Request processing
    print("Requesting image processing (grayscale)...\n")
    process_resp = requests.post(
        f"{GATEWAY_URL}/buckets/{bucket_id}/objects/{file_id}/process",
        json={"operation": "grayscale"}
    )
    
    if process_resp.status_code != 200:
        print(f"Failed to request processing: {process_resp.text}\n")
        return
    
    print(f"Processing started: {process_resp.json()}\n")
    
    # 4. Wait for processing
    print("Waiting for processing (10 seconds)...\n")
    time.sleep(10)
    
    # 5. Check if output file was created
    print("Checking files in bucket...\n")
    files_resp = requests.get(f"{GATEWAY_URL}/buckets/{bucket_id}/files")
    files_data = files_resp.json()
    
    print(f"Files in bucket: {len(files_data)}\n")
    for file in files_data:
        print(f"  - {file['filename']} (ID: {file['id']})\n")
    
    # 6. Get bucket stats
    print("Bucket statistics:\n")
    stats_resp = requests.get(f"{GATEWAY_URL}/buckets/{bucket_id}/stats")
    stats = stats_resp.json()
    
    print(f"  - Bandwidth: {stats['bandwidth_bytes']} bytes\n")
    print(f"  - Read requests: {stats['count_read_requests']}\n")
    print(f"  - Write requests: {stats['count_write_requests']}\n")
    
    print("Flow completed successfully!\n")


if __name__ == "__main__":
    test_complete_flow()
