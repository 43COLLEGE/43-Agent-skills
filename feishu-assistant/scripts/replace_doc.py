"""Replace Feishu document content (delete all blocks, then write new content)"""
import json, sys, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from feishu_client import FeishuClient

config = json.loads(Path(__file__).with_name("config.json").read_text(encoding="utf-8"))
token_file = str(Path(__file__).parent / "cache" / "user_token.json")
client = FeishuClient(config["app_id"], config["app_secret"], user_token_file=token_file)

doc_token = sys.argv[1]
content_file = sys.argv[2] if len(sys.argv) > 2 else None
base_url = "https://open.feishu.cn/open-apis"

# Get user token
user_token = client.get_user_access_token()
headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}

# Step 1: Get all blocks
print("Getting all blocks...")
resp = requests.get(f"{base_url}/docx/v1/documents/{doc_token}/blocks", headers=headers)
items = resp.json().get("data", {}).get("items", [])
page_block_id = items[0]["block_id"]

child_ids = [item["block_id"] for item in items if item.get("parent_id") == page_block_id]
print(f"Found {len(child_ids)} child blocks to delete")

# Step 2: Delete all child blocks using batch delete
# Feishu API: DELETE /docx/v1/documents/{document_id}/blocks/{block_id}/children/batch_delete
# Actually, we need to delete individual blocks
deleted = 0
failed = 0
for cid in reversed(child_ids):
    resp = requests.delete(f"{base_url}/docx/v1/documents/{doc_token}/blocks/{cid}", headers=headers)
    if resp.status_code == 200:
        try:
            result = resp.json()
            if result.get("code") == 0:
                deleted += 1
            else:
                # Try batch delete approach - delete children of page block
                failed += 1
        except:
            # Empty response body is OK for DELETE
            deleted += 1
    else:
        failed += 1
    time.sleep(0.05)

print(f"Deleted: {deleted}, Failed: {failed}")

if failed > 0:
    print("Some blocks failed to delete. Trying batch approach...")
    # Use the batch delete endpoint
    payload = {
        "start_index": 0,
        "end_index": len(child_ids)
    }
    resp = requests.delete(
        f"{base_url}/docx/v1/documents/{doc_token}/blocks/{page_block_id}/children/batch_delete",
        headers=headers,
        json=payload
    )
    print(f"Batch delete response: {resp.status_code}")
    try:
        print(resp.json())
    except:
        print(resp.text[:200])

# Step 3: Write new content
if content_file:
    content = Path(content_file).read_text(encoding="utf-8")
    print(f"Writing new content ({len(content)} chars)...")
    client.update_document(doc_token, content)
    print("Done!")
else:
    print("Document cleared.")
