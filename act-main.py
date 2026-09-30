from datetime import datetime, timezone
import requests

# Khởi tạo API URL của ActivityWatch
AW_URL = "http://localhost:5600/api/0"


def find_bucket(prefix):
  """Tìm bucket ID dựa theo tiền tố tên bucket"""
  try:
    buckets = requests.get(f"{AW_URL}/buckets").json()
    for bucket_id in buckets:
      if prefix in bucket_id:
        return bucket_id
  except Exception as e:
    print(f"Lỗi khi kết nối ActivityWatch: {e}")
  return None


def query_bucket(bucket_id):
  """Lấy toàn bộ sự kiện từ một bucket"""
  if not bucket_id:
    return []
  try:
    return requests.get(f"{AW_URL}/buckets/{bucket_id}/events").json()
  except Exception as e:
    print(f"Lỗi khi lấy sự kiện từ bucket {bucket_id}: {e}")
    return []


def filter_keyvals(events, key, values):
  """Lọc các sự kiện có chứa key và giá trị nằm trong danh sách values"""
  filtered = []
  for e in events:
    data = e.get("data", {})
    if data.get(key) in values:
      filtered.append(e)
  return filtered


def filter_period_intersect(events, afk_not_events):
  """Giao (intersect) thời gian của events với các khoảng thời gian not-afk"""
  intersected_events = []

  for w in events:
    w_start = datetime.fromisoformat(w["timestamp"].replace("Z", "+00:00"))
    w_duration = w.get("duration", 0)
    w_end = w_start.timestamp() + w_duration

    for a in afk_not_events:
      a_start = datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00"))
      a_duration = a.get("duration", 0)
      a_end = a_start.timestamp() + a_duration

      # Tính khoảng thời gian giao nhau giữa window event và afk event
      intersect_start = max(w_start.timestamp(), a_start.timestamp())
      intersect_end = min(w_end, a_end)

      if intersect_start < intersect_end:
        # Tạo bản sao sự kiện window với thời gian và duration mới đã được cắt gọt theo khoảng not-afk
        new_event = w.copy()
        new_event["timestamp"] = (
            datetime.fromtimestamp(intersect_start, timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        new_event["duration"] = intersect_end - intersect_start
        intersected_events.append(new_event)

  return intersected_events


# --- THỰC THI CHÍNH ---
afk_bucket = find_bucket("aw-watcher-afk")
window_bucket = find_bucket("aw-watcher-window")

afk_events = query_bucket(afk_bucket)
events = query_bucket(window_bucket)

# Lọc các sự kiện afk có trạng thái "not-afk"
not_afk_events = filter_keyvals(afk_events, "status", ["not-afk"])

# Lọc và cắt giao các sự kiện window theo thời gian không bị AFK
events = filter_period_intersect(events, not_afk_events)

# 1. Lấy danh sách bucket và tìm aw-watcher-window
buckets_url = "http://localhost:5600/api/0/buckets"
buckets = requests.get(buckets_url).json()
window_bucket_id = next(
    (b for b in buckets if "aw-watcher-window" in b), None
)

if window_bucket_id:
  events_url = f"http://localhost:5600/api/0/buckets/{window_bucket_id}/events"
  raw_events = requests.get(events_url).json()

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
    # 1. Nếu là Google Chrome, app phải giống nhau và phần đầu của title cũng phải giống nhau
    # 2. Nếu là Code hoặc iTerm2, miễn là các sự kiện liên tiếp nằm trong nhóm 2 app này thì gộp tất cả vào nhau
    # 3. Các app khác thì chỉ cần trùng tên app là gộp
    if processed_events:
      last_event = processed_events[-1]
      last_data = last_event.get("data", {})
      last_app = last_data.get("app", "")

      # Bỏ qua các sự kiện loginwindow
      if app_name == "loginwindow":
        continue

      # Định nghĩa nhóm dev (Code và iTerm2)
      dev_apps = ["Code", "iTerm2"]

      if app_name == "Google Chrome" and last_app == "Google Chrome":
        last_title = last_data.get("title", "")
        last_main_title = (
            last_title.split("-")[0].strip() if last_title else ""
        )
        if last_main_title == chrome_main_title:
          last_event["duration"] += e.get("duration", 0)
          continue
      elif app_name in dev_apps and last_app in dev_apps:
        # Gộp chung Code và iTerm2 khi đứng liên tiếp nhau
        last_event["duration"] += e.get("duration", 0)
        continue
      elif last_app == app_name and app_name not in dev_apps:
        # Đối với các app thông thường khác, trùng tên app là gộp
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

    for e in processed_events[-100:]:  # Chỉ in ra 100 sự kiện gần nhất
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
        max_title_len = 90
        if app_name == "Google Chrome":
          # max_title_len = 90
          # if len(title) > max_title_len:
          #   title = title[:max_title_len] + "..."
          display_name = f"Chrome: {title}"
          display_name = display_name if len(display_name) <= max_title_len else display_name[:max_title_len-3] + "..."

        else:
          display_name = app_name

        # Quy đổi thời lượng sang phút/giây
        duration_str = f"{duration:.1f} giây" f" - ({duration / 60:.1f} phút)"

        print(f"{time_str:<20} | {display_name:<90} | {duration_str:<20}")

    print("\n--- THỐNG KÊ ---")
    print(
    f"Số lượng sự kiện window trước khi lọc AFK:"
    f" {len(raw_events)}")
    print(
    f"Số lượng sự kiện window sau khi lọc AFK:"
    f" {len(events)}")
    print(f"Tổng số task/task nhóm sau khi xử lý: {len(durations)}")
    print(
        f"Thời gian trung bình mỗi task/nhóm: {avg_duration:.2f} giây"
        f" ({avg_duration / 60:.2f} phút)\n"
    )
else:
    print("Không tìm thấy bucket window.")