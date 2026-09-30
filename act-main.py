from datetime import datetime, timezone
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
    data = e.get("data", {})
    app_name = data.get("app", "")
    title = data.get("title", "")

    # Lấy phần đầu tiên của title nếu là Google Chrome (phân cách bởi dấu '-')
    chrome_main_title = ""
    if app_name == "Google Chrome" and title:
      chrome_main_title = title.split("-")[0].strip()

    # Gộp các sự kiện liên tiếp nếu:
    # 1. Sự kiện ngay trước đó có cùng app_name
    # 2. Nếu là Google Chrome, phần đầu của title cũng phải giống nhau
    if processed_events:
      last_event = processed_events[-1]
      last_data = last_event.get("data", {})
      last_app = last_data.get("app", "")

      if last_app == app_name:
        if app_name == "Google Chrome":
          last_title = last_data.get("title", "")
          last_main_title = (
              last_title.split("-")[0].strip() if last_title else ""
          )
          if last_main_title == chrome_main_title:
            last_event["duration"] += e.get("duration", 0)
            continue
        else:
          # Đối với app khác (không phải Chrome), chỉ cần trùng tên app là gộp
          last_event["duration"] += e.get("duration", 0)
          continue

    processed_events.append(e)

  # Lọc các duration hợp lệ (>0) để tính toán
  durations = [
      e["duration"]
      for e in processed_events
      if isinstance(e.get("duration"), (int, float)) and e["duration"] > 0
  ]

  if durations:
    avg_duration = sum(durations) / len(durations)

    # --- IN RA DANH SÁCH TASK ---
    print("--- DANH SÁCH TASK/APP ---")
    print(f"{'Thời điểm':<20} | {'Ứng dụng / Tab (Title)':<50} | {'Thời lượng':<15}")
    print("-" * 91)

    # Lấy thời điểm hiện tại theo UTC
    now = datetime.now(timezone.utc)

    for e in processed_events:
      duration = e.get("duration", 0)
      if isinstance(duration, (int, float)) and duration > 0:
        raw_time = e.get("timestamp", "")
        time_str = raw_time
        try:
          dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
          diff_seconds = (now - dt).total_seconds()

          if diff_seconds < 60:
            time_str = "Vừa xong"
          elif diff_seconds < 3600:
            minutes = int(diff_seconds // 60)
            time_str = f"{minutes} phút trước"
          elif diff_seconds < 86400:
            hours = int(diff_seconds // 3600)
            time_str = f"{hours} giờ trước"
          else:
            days = int(diff_seconds // 86400)
            time_str = f"{days} ngày trước"
        except Exception:
          pass

        app_data = e.get("data", {})
        app_name = app_data.get("app", "Unknown")
        title = app_data.get("title", "")

        # Xử lý hiển thị title của Chrome (cắt ngắn nếu quá dài)
        if app_name == "Google Chrome":
          max_title_len = 35
          if len(title) > max_title_len:
            title = title[:max_title_len] + "..."
          display_name = f"Chrome: {title}"
        else:
          display_name = app_name

        # Quy đổi thời lượng sang phút/giây
        if duration >= 60:
          duration_str = f"{duration / 60:.1f} phút"
        else:
          duration_str = f"{duration:.1f} giây"

        print(f"{time_str:<20} | {display_name:<50} | {duration_str:<15}")

    print("\n--- THỐNG KÊ ---")
    print(f"Tổng số task/task nhóm sau khi xử lý: {len(durations)}")
    print(
        f"Thời gian trung bình mỗi task/nhóm: {avg_duration / 60:.2f} phút"
        f" ({avg_duration:.2f} giây)\n"
    )
else:
    print("Không tìm thấy bucket window.")