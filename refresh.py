import json
import os
import sys
import urllib.request
import urllib.parse

def load_local_env():
    """Load simple KEY=VALUE pairs for local testing; GitHub Actions still uses secrets."""
    for filename in (".env.local", ".env"):
        if not os.path.exists(filename):
            continue
        with open(filename, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)

load_local_env()

APP_TOKEN = os.environ.get("LARK_BASE_TOKEN", "").strip()
TABLE_ID = os.environ.get("LARK_TABLE_ID", "").strip()
OUTPUT_FILE = os.path.join("api", "videos.json")

FIELD_TITLE = os.environ.get("FIELD_TITLE", "内容")
FIELD_VIDEO = os.environ.get("FIELD_VIDEO", "样片")
FIELD_TYPE = os.environ.get("FIELD_TYPE", "类型")
FIELD_DURATION = os.environ.get("FIELD_DURATION", "时长")
FIELD_TOOL = os.environ.get("FIELD_TOOL", "AI工具")
FIELD_ORDER = os.environ.get("FIELD_ORDER", "序号")
FIELD_DESC = os.environ.get("FIELD_DESC", "说明")
FIELD_COVER_URL = os.environ.get("FIELD_COVER_URL", "封面URL")
FIELD_COVER_LOCAL = os.environ.get("FIELD_COVER_LOCAL", "封面本地路径")
FIELD_VIDEO_URL = os.environ.get("FIELD_VIDEO_URL", "URL")
FIELD_VIDEO_LOCAL = os.environ.get("FIELD_VIDEO_LOCAL", "样片本地路径")
REPO_PATH_MARKER = "/feishu-website/"

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
    except urllib.error.HTTPError as e:
        print(f"Auth request exception: HTTP {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Auth request exception: {e}")
    return None

def get_bitable_records(token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    all_records = []
    has_more = True
    page_token = ""
    
    while has_more:
        try:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token
            page_url = f"{url}?{urllib.parse.urlencode(params)}"
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
        except urllib.error.HTTPError as e:
            print(f"Bitable API exception: HTTP {e.code} - {e.read().decode('utf-8')}")
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
    except urllib.error.HTTPError as e:
        print(f"Failed to fetch URLs: HTTP {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Failed to fetch URLs: {e}")
    return None

def normalize_field_text(value):
    if isinstance(value, list):
        return "".join(normalize_field_text(item) for item in value)
    if isinstance(value, dict):
        return str(value.get("text") or value.get("name") or value.get("url") or "").strip()
    return str(value or "").strip()

def local_path_to_site_url(value):
    text = normalize_field_text(value)
    if not text:
        return ""
    if text.startswith(("http://", "https://", "./", "/assets/")):
        return text
    if REPO_PATH_MARKER in text:
        return "./" + text.split(REPO_PATH_MARKER, 1)[1].lstrip("/")
    return ""

def load_existing_records():
    if not os.path.exists(OUTPUT_FILE):
        return {}
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        return {str(item.get("序号")): item for item in existing if item.get("序号") is not None}
    except Exception as e:
        print(f"Could not read existing {OUTPUT_FILE}: {e}")
        return {}

def main():
    app_id = os.environ.get("LARK_APP_ID")
    app_secret = os.environ.get("LARK_APP_SECRET")
    
    if not app_id or not app_secret or not APP_TOKEN or not TABLE_ID:
        print("Missing GitHub Secrets! Please configure LARK_APP_ID, LARK_APP_SECRET, LARK_BASE_TOKEN, LARK_TABLE_ID.")
        sys.exit(1)
        
    print("Authenticating...")
    tenant_token = get_tenant_token(app_id, app_secret)
    if not tenant_token:
        print("Could not obtain tenant access token. Aborting.")
        sys.exit(1)

    print("Fetching live records from Bitable...")
    records = get_bitable_records(tenant_token)
    print(f"Found {len(records)} records in Bitable.")
    if not records:
        print("No Bitable records found. Keeping existing api/videos.json unchanged.")
        sys.exit(1)

    # Sort records by custom field '序号' if you like, or leave as is
    def get_order(record):
        try:
            return float(record.get('fields', {}).get(FIELD_ORDER, 0))
        except:
            return 0
    records.sort(key=get_order)

    # Collect tokens
    tokens_to_fetch = []
    for r in records:
        fields = r.get("fields", {})
        attachments = fields.get(FIELD_VIDEO, [])
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

    existing_by_order = load_existing_records()

    # Build final formatted JSON array for frontend. Attachment URLs win; existing
    # repo-relative URLs and local-path fields keep the archive stable during migration.
    final_output = []
    for r in records:
        fields = r.get("fields", {})
        order = get_order(r)
        existing = existing_by_order.get(str(order), {})
        attachments = fields.get(FIELD_VIDEO, [])
        resolved_url = ""
        if attachments and isinstance(attachments, list) and len(attachments) > 0:
            token = attachments[0].get("file_token")
            if token in mapped_urls:
                resolved_url = mapped_urls[token]

        direct_video_url = local_path_to_site_url(fields.get(FIELD_VIDEO_URL, ""))
        local_video_url = local_path_to_site_url(fields.get(FIELD_VIDEO_LOCAL, ""))
        direct_cover_url = local_path_to_site_url(fields.get(FIELD_COVER_URL, ""))
        local_cover_url = local_path_to_site_url(fields.get(FIELD_COVER_LOCAL, ""))

        merged = {
            "内容": fields.get(FIELD_TITLE, "") or existing.get("内容", ""),
            "序号": order,
            "类型": fields.get(FIELD_TYPE, []) or existing.get("类型", []),
            "时长": fields.get(FIELD_DURATION, "") or existing.get("时长", ""),
            "AI工具": fields.get(FIELD_TOOL, "") or existing.get("AI工具", ""),
            "说明": fields.get(FIELD_DESC, "") or existing.get("说明", ""),
            "封面URL": direct_cover_url or local_cover_url or existing.get("封面URL", ""),
            "URL": resolved_url or direct_video_url or local_video_url or existing.get("URL", "")
        }

        if merged["内容"] and (merged["URL"] or merged["封面URL"]):
            final_output.append(merged)

    if not final_output:
        print(
            f"No playable videos or covers were resolved from Feishu fields. "
            "Keeping existing api/videos.json unchanged."
        )
        sys.exit(1)

    if existing_by_order and len(final_output) < len(existing_by_order):
        print(
            f"Resolved {len(final_output)} items, fewer than existing {len(existing_by_order)}. "
            "Keeping existing api/videos.json unchanged to avoid shrinking the public archive."
        )
        sys.exit(1)

    os.makedirs("api", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated full mapped datastore with {len(final_output)} items to api/videos.json!")

if __name__ == "__main__":
    main()
