#!/usr/bin/env python3
"""queue.json の先頭から未投稿の1件を Instagram に投稿する。

必要な環境変数:
  IG_USER_ID       Instagram ビジネスアカウントの ID（数字）
  IG_ACCESS_TOKEN  instagram_content_publish 権限を持つアクセストークン
  IMAGE_BASE_URL   画像を公開しているURLの接頭辞（末尾スラッシュなし）
  DRY_RUN          "true" のとき、API を呼ばずに内容だけ表示する
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://graph.facebook.com/v21.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "queue.json")

USER_ID = os.environ.get("IG_USER_ID", "")
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
BASE_URL = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
DRY_RUN = os.environ.get("DRY_RUN", "").lower() == "true"


def call(path, params, method="GET"):
    params = dict(params, access_token=TOKEN)
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        req = urllib.request.Request(f"{API}/{path}?{data.decode()}")
    else:
        req = urllib.request.Request(f"{API}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise SystemExit(f"Instagram API エラー ({e.code}): {body}")


def wait_ready(container_id, tries=20, wait=5):
    """コンテナの処理完了を待つ。"""
    for _ in range(tries):
        info = call(container_id, {"fields": "status_code,status"})
        code = info.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise SystemExit(f"コンテナの処理に失敗しました: {info}")
        time.sleep(wait)
    raise SystemExit(f"コンテナの処理が {tries * wait} 秒以内に終わりませんでした: {container_id}")


def main():
    posts = json.load(open(QUEUE, encoding="utf-8"))
    remaining = [p for p in posts if not p.get("posted_at") and not p.get("hold")]
    if not remaining:
        print("::error::queue.json に未投稿の投稿がありません。次の投稿を追加してください。")
        return 1

    # 予約実行が複数回起動しても、1日1件だけ投稿する
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))
    posted_today = [p for p in posts if str(p.get("posted_at") or "").startswith(today)]
    if posted_today and os.environ.get("FORCE", "").lower() != "true":
        print(f"今日（{today}）はすでに投稿済みです: {posted_today[-1]['id']} {posted_today[-1]['title']}")
        return 0

    post = remaining[0]
    urls = [f"{BASE_URL}/{name}" for name in post["images"]]
    print(f"投稿: {post['id']} {post['title']}")
    print(f"画像: {len(urls)}枚 / 残り（この1件を含む）: {len(remaining)}件")

    if DRY_RUN:
        print("--- DRY_RUN のため API は呼びません ---")
        for u in urls:
            print(u)
        print(post["caption"])
        return 0

    for key in ("IG_USER_ID", "IG_ACCESS_TOKEN", "IMAGE_BASE_URL"):
        if not os.environ.get(key):
            raise SystemExit(f"環境変数 {key} が設定されていません。")

    children = []
    for url in urls:
        res = call(f"{USER_ID}/media", {"image_url": url, "is_carousel_item": "true"}, "POST")
        wait_ready(res["id"])
        children.append(res["id"])
        print(f"  アイテム作成: {res['id']}")

    parent = call(
        f"{USER_ID}/media",
        {"media_type": "CAROUSEL", "children": ",".join(children), "caption": post["caption"]},
        "POST",
    )
    wait_ready(parent["id"])
    published = call(f"{USER_ID}/media_publish", {"creation_id": parent["id"]}, "POST")
    print(f"公開しました: media_id={published['id']}")

    post["posted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.gmtime(time.time() + 9 * 3600))
    post["media_id"] = published["id"]
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
        f.write("\n")

    left = len([p for p in posts if not p.get("posted_at") and not p.get("hold")])
    print(f"残り: {left}件")
    if left == 0:
        print("::warning::これが最後の投稿でした。次の投稿を追加してください。")
    elif left <= 3:
        print(f"::warning::残り{left}件です。そろそろ次の投稿を用意してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
