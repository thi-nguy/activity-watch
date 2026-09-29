from datetime import datetime, timezone
import requests

# 1. Tìm đúng bucket window trên máy Mac của bạn
buckets_url = "http://localhost:5600/api/0/buckets"
buckets = requests.get(buckets_url).json()
window_bucket_id = next(
    (b for b in buckets if "aw-watcher-window" in b), None
)

if window_bucket_id:
  # 2. Lấy toàn bộ sự kiện
  events_url = f"http://localhost:5600/api/0/buckets/{window_bucket_id}/events"
  events = requests.get(events_url).json()

  # 3. Sắp xếp tăng dần theo thời gian, sau đó đảo ngược để đưa sự kiện mới nhất lên đầu
  events_sorted = sorted(events, key=lambda x: x["timestamp"])

  print(f"Đã lấy thành công {len(events_sorted)} sự kiện mới nhất:\n")

  now = datetime.now(timezone.utc)  # Lấy thời gian hiện tại theo chuẩn UTC

  for i, e in enumerate(events_sorted, 1):
    app = e.get("data", {}).get("app", "Unknown")
    title = e.get("data", {}).get("title", "No title")
    duration = e.get("duration", 0)
    timestamp_str = e.get("timestamp", "")

    # Chuyển đổi timestamp thành dạng "X minutes ago"
    time_ago_str = "Unknown time"
    try:
      # Parse chuỗi timestamp ISO từ ActivityWatch
      event_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
      diff_seconds = (now - event_time).total_seconds()

      if diff_seconds < 60:
        time_ago_str = f"{int(diff_seconds)}s ago"
      elif diff_seconds < 3600:
        time_ago_str = f"{int(diff_seconds // 60)} minutes ago"
      else:
        time_ago_str = f"{int(diff_seconds // 3600)} hours ago"
    except Exception:
      pass

    print(
        f"{i}. [{time_ago_str}] - [{duration:.1f}s] - App: {app} - Title:"
        f" {title}"
    )
else:
  print("Không tìm thấy bucket window.")