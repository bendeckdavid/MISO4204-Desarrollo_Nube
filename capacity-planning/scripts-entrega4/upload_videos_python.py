#!/usr/bin/env python3
"""
Script to upload multiple videos to test SQS worker autoscaling
"""
import requests
import sys
import time

ALB_DNS = "http://anb-video-alb-1059958631.us-east-1.elb.amazonaws.com"
VIDEO_FILE = "/tmp/test_video.mp4"
NUM_VIDEOS = 12

print("🔐 Autenticando...")
login_response = requests.post(
    f"{ALB_DNS}/api/auth/login",
    json={"email": "test1@anb.com", "password": "Test123!"}
)

if login_response.status_code != 200:
    print(f"❌ Error al autenticar: {login_response.text}")
    sys.exit(1)

token = login_response.json()["access_token"]
print(f"✅ Token obtenido")

headers = {"Authorization": f"Bearer {token}"}

print(f"\n📤 Subiendo {NUM_VIDEOS} videos...")
success_count = 0
failed_count = 0

for i in range(1, NUM_VIDEOS + 1):
    print(f"   [{i:2d}/{NUM_VIDEOS}] Subiendo video... ", end="", flush=True)

    try:
        with open(VIDEO_FILE, 'rb') as f:
            files = {'file': (f'test_video_{i}.mp4', f, 'video/mp4')}
            data = {
                'title': f'Test Video {i} - Auto Scaling',
                'description': 'Worker Auto Scaling Test - Entrega 4'
            }

            response = requests.post(
                f"{ALB_DNS}/api/videos",
                headers=headers,
                files=files,
                data=data,
                allow_redirects=True,
                timeout=30
            )

            if response.status_code in [200, 201]:
                print(f"✅ (HTTP {response.status_code})")
                success_count += 1
            else:
                print(f"❌ (HTTP {response.status_code})")
                print(f"      Response: {response.text[:100]}")
                failed_count += 1

    except Exception as e:
        print(f"❌ Error: {e}")
        failed_count += 1

    time.sleep(0.5)

print(f"\n✅ Uploads completados")
print(f"   Exitosos: {success_count}")
print(f"   Fallidos: {failed_count}")

sys.exit(0 if success_count > 0 else 1)
