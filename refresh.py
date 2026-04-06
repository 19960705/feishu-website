import json
import subprocess
import os
import urllib.request

TABLE_ID = "tblLPKUMFfUdMe3Y"
DATA_FILE = "feishu_data.json"
OUTPUT_FILE = os.path.join("api", "videos.json")

def get_tenant_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read())
            if res.get("code") == 0:
                return res.get("tenant_access_token")
            else:
                print(f"Failed to get tenant token: {res}")
    except Exception as e:
        print(f"Auth request exception: {e}")
    return None

def fetch_with_api(token, batch):
    url = "https://open.feishu.cn/open-apis/drive/v1/medias/batch_get_tmp_download_url"
    extra_json = json.dumps({"bitablePerm": {"tableId": TABLE_ID}})
    
    # Construct query params
    params = f"extra={urllib.parse.quote(extra_json)}"
    for t in batch:
        params += f"&file_tokens={t}"
        
    full_url = f"{url}?{params}"
    req = urllib.request.Request(full_url, headers={"Authorization": f"Bearer {token}"})
    
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read())
            return res
    except Exception as e:
        print(f"Failed to fetch URLs: {e}")
    return None

def main():
    print("Loading feishu_data.json...")
    try:
        with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load data: {e}")
        return

    tokens = []
    rows = data.get("data", {}).get("data", [])
    for row in rows:
        if len(row) > 3:
            attachments = row[3]
            if isinstance(attachments, list) and len(attachments) > 0:
                tokens.append(attachments[0].get("file_token"))

    tokens = [t for t in tokens if t]
    print(f"Found {len(tokens)} video tokens.")
    if not tokens:
        return

    # Check if we are running in CI (GitHub Actions)
    app_id = os.environ.get("LARK_APP_ID")
    app_secret = os.environ.get("LARK_APP_SECRET")
    tenant_token = None
    
    if app_id and app_secret:
        print("CI environment detected: Authenticating via Feishu OpenAPI...")
        tenant_token = get_tenant_token(app_id, app_secret)
        if not tenant_token:
            print("Could not obtain tenant access token. Aborting.")
            return
    else:
        print("Local environment detected: Falling back to lark-cli...")

    mapped_urls = {}
    
    # Process in batches of 5
    for i in range(0, len(tokens), 5):
        batch = tokens[i:i+5]
        print(f"Fetching batch {i//5 + 1}...")
        
        if tenant_token:
            import urllib.parse
            response_data = fetch_with_api(tenant_token, batch)
        else:
            # Fallback to local lark-cli command
            extra_json = json.dumps({"bitablePerm": {"tableId": TABLE_ID}})
            params_dict = {"file_tokens": batch, "extra": extra_json}
            
            cmd = ["npx.cmd", "lark-cli", "api", "GET", "/open-apis/drive/v1/medias/batch_get_tmp_download_url", "--params", json.dumps(params_dict)]
            
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
                if res.returncode != 0:
                    print(f"Command failed:\n{res.stderr}")
                    continue
                out = res.stdout.strip()
                if not out: continue
                response_data = json.loads(out)
            except Exception as e:
                print(f"Subprocess Exception: {e}")
                continue

        if response_data and (response_data.get("code") == 0 or response_data.get("ok")):
            tmp_urls = response_data.get("data", {}).get("tmp_download_urls", [])
            for item in tmp_urls:
                mapped_urls[item["file_token"]] = item["tmp_download_url"]
        else:
            print(f"API Error in batch {i//5 + 1}: {response_data}")

    os.makedirs("api", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapped_urls, f, indent=2)
        
    print(f"Successfully mapped {len(mapped_urls)} videos to api/videos.json!")

if __name__ == "__main__":
    main()
