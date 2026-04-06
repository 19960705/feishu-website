import json
import subprocess
import sys
import os

TABLE_ID = "tblLPKUMFfUdMe3Y"
DATA_FILE = "feishu_data.json"
OUTPUT_FILE = os.path.join("api", "videos.json")

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

    # filter None
    tokens = [t for t in tokens if t]
    print(f"Found {len(tokens)} video tokens.")
    if not tokens:
        return

    mapped_urls = {}
    
    # Process in batches of 5
    for i in range(0, len(tokens), 5):
        batch = tokens[i:i+5]
        print(f"Fetching batch {i//5 + 1}...")
        
        # Build params JSON
        extra_json = json.dumps({"bitablePerm": {"tableId": TABLE_ID}})
        params_dict = {
            "file_tokens": batch,
            "extra": extra_json
        }
        params_str = json.dumps(params_dict)
        
        cmd = ["npx.cmd", "lark-cli", "api", "GET", "/open-apis/drive/v1/medias/batch_get_tmp_download_url", "--params", params_str]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if res.returncode != 0:
                print(f"Command failed (Return code {res.returncode}):\n{res.stderr}")
                continue
                
            out = res.stdout.strip()
            # Try to parse the JSON output from lark-cli
            if not out:
                print("No output received from lark-cli.")
                if res.stderr:
                    print(f"Stderr: {res.stderr}")
                continue
                
            response_data = json.loads(out)
            
            if response_data.get("code") == 0 or response_data.get("ok"):
                tmp_urls = response_data.get("data", {}).get("tmp_download_urls", [])
                for item in tmp_urls:
                    mapped_urls[item["file_token"]] = item["tmp_download_url"]
            else:
                print(f"API Error in batch {i//5 + 1}: {out}")
        except Exception as e:
            print(f"Subprocess Exception: {e}")

    # Ensure api folder exists
    os.makedirs("api", exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapped_urls, f, indent=2)
        
    print(f"Successfully mapped {len(mapped_urls)} videos to api/videos.json!")

if __name__ == "__main__":
    main()
