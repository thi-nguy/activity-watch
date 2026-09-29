import requests

# 1. Lấy danh sách bucket và tìm aw-watcher-window
buckets_url = "http://localhost:5600/api/0/buckets"
buckets = requests.get(buckets_url).json()
window_bucket_id = next(
    (b for b in buckets if "aw-watcher-window" in b), None
)

if window_bucket_id:
  events_url = f"http://localhost:5600/api/0/buckets/{window_bucket_id}/events"
  events = requests.get(events_url).json()

  # Sắp xếp sự kiện theo thời gian tăng dần
  events = sorted(events, key=lambda x: x["timestamp"])

  processed_events = []
  for e in events:
    app_name = e.get("data", {}).get("app", "")

    # Gộp các sự kiện liên tiếp nếu:
    # 1. Không phải là Google Chrome (tức là app khác như iTerm2, VS Code, Finder, v.v.)
    # 2. Sự kiện ngay trước đó cũng có cùng tên app
    if app_name != "Google Chrome" and processed_events:
      last_event = processed_events[-1]
      last_app = last_event.get("data", {}).get("app", "")

      if last_app == app_name:
        # Cộng dồn thời lượng (duration) vào sự kiện trước đó của cùng app đó
        last_event["duration"] += e.get("duration", 0)
        continue

    # Riêng Google Chrome hoặc các app khác không đứng liền nhau thì giữ nguyên
    processed_events.append(e)

  # Lọc các duration hợp lệ (>0) để tính toán
  durations = [
      e["duration"]
      for e in processed_events
      if isinstance(e.get("duration"), (int, float)) and e["duration"] > 0
  ]

  if durations:
    avg_duration = sum(durations) / len(durations)
    print(f"Tổng số task/tab sau khi xử lý: {len(durations)}")
    print(
        f"Thời gian trung bình mỗi task/tab: {avg_duration / 60:.2f} phút"
        f" ({avg_duration:.2f} giây)"
    )
else:
  print("Không tìm thấy bucket window.")