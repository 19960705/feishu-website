import json
import os
import urllib.request
import urllib.parse

APP_TOKEN = "PDk1bzTduaoYTmsmnqWcIp7BnS4"
TABLE_ID = "tblLPKUMFfUdMe3Y"
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

def get_bitable_records(token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    all_records = []
    has_more = True
    page_token = ""
    
    while has_more:
        try:
            page_url = url
            if page_token:
                page_url += f"?page_token={page_token}"
            req = urllib.request.Request(page_url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read())
                if res.get("code") == 0:
                    data = res.get("data", {})
                    all_records.extend(data.get("items", []))
                    has_more = data.get("has_more", False)
                    page_token = data.get("page_token", "")
                else:
                    print(f"Failed to fetch records: {res}")
                    break
        except Exception as e:
            print(f"Bitable API exception: {e}")
            break
    return all_records

def fetch_media_urls(token, batch):
    url = "https://open.feishu.cn/open-apis/drive/v1/medias/batch_get_tmp_download_url"
    extra_json = json.dumps({"bitablePerm": {"tableId": TABLE_ID}})
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
    app_id = os.environ.get("LARK_APP_ID")
    app_secret = os.environ.get("LARK_APP_SECRET")
    
    if not app_id or not app_secret:
        print("Missing GitHub Secrets LARK_APP_ID / LARK_APP_SECRET! Please configure them.")
        return
        
    print("Authenticating...")
    tenant_token = get_tenant_token(app_id, app_secret)
    if not tenant_token:
        print("Could not obtain tenant access token. Aborting.")
        return

    print("Fetching live records from Bitable...")
    records = get_bitable_records(tenant_token)
    print(f"Found {len(records)} records in Bitable.")

    # Sort records by custom field '序号' if you like, or leave as is
    def get_order(record):
        try:
            return float(record.get('fields', {}).get('序号', 0))
        except:
            return 0
    records.sort(key=get_order)

    # Collect tokens
    tokens_to_fetch = []
    for r in records:
        fields = r.get("fields", {})
        attachments = fields.get("样片", [])
        if attachments and isinstance(attachments, list) and len(attachments) > 0:
            tokens_to_fetch.append(attachments[0].get("file_token"))
            
    print(f"Found {len(tokens_to_fetch)} video tokens to resolve.")
    
    # Resolve tokens
    mapped_urls = {}
    for i in range(0, len(tokens_to_fetch), 5):
        batch = tokens_to_fetch[i:i+5]
        print(f"Fetching batch {i//5 + 1}...")
        response_data = fetch_media_urls(tenant_token, batch)
        if response_data and response_data.get("code") == 0:
            tmp_urls = response_data.get("data", {}).get("tmp_download_urls", [])
            for item in tmp_urls:
                mapped_urls[item["file_token"]] = item["tmp_download_url"]

    # Build final formatted JSON array for frontend
    final_output = []
    for r in records:
        fields = r.get("fields", {})
        attachments = fields.get("样片", [])
        if attachments and isinstance(attachments, list) and len(attachments) > 0:
            token = attachments[0].get("file_token")
            # Only add if we successfully resolved the URL
            if token in mapped_urls:
                final_output.append({
                    "内容": fields.get("内容", ""),
                    "序号": get_order(r),
                    "类型": fields.get("类型", []),
                    "时长": fields.get("时长", ""),
                    "AI工具": fields.get("AI工具", ""),
                    "URL": mapped_urls[token]
                })

    os.makedirs("api", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated full mapped datastore with {len(final_output)} items to api/videos.json!")

if __name__ == "__main__":
    main()
