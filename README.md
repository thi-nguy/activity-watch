# ActivityWatch Window Event Processor

- Over the past two decades, researchers have found that the average time people stay focused on a single task has dropped from about 2.5 minutes (150 seconds, in 2003) to roughly 40 seconds (in 2024).

- This project contains Python scripts to fetch, clean, group, and analyze window activity logs from **ActivityWatch**. It helps you understand how you spend your time on your computer.

## Features

- **Bucket Detection:** Connects to your local ActivityWatch server (`http://localhost:5600`) and finds the window watcher bucket.
- **Event Grouping:**
  - Groups consecutive events from applications (e.g., VS Code, iTerm2, Finder).
  - Groups Google Chrome tabs by extracting the primary title segment (split by `-`) so that switching between minor sub-states on the same webpage doesn't fragment your history.
- **Relative Timestamps:** Converts UTC ISO timestamps into friendly relative strings (e.g., "Vừa xong", "5 phút trước", "2 giờ trước").
- **Clean Terminal Output:** Displays summary table of your tasks/apps along with calculated averages and total task counts.

## Prerequisites

- Make sure you have **ActivityWatch** installed and running locally.
- To track tab on your browser, make sure install extenstion for **ActivityWatch**.
- Make sure you have Python and needed library installed.

## List of files

1. `act-detail-list.py`: raw list from Activity Watch.
2. `act-summary.py`: Give total grouped tasks and average time of doing a task before jumping to another task.
3. `act-main.py`: Give grouped task list + average time.

## Output Example

```text
--- DANH SÁCH TASK/APP ---
Thời điểm (Timestamp)| Ứng dụng / Tab (Title)                             | Thời lượng (duration)
-------------------------------------------------------------------------------------------
15 phút trước        | Chrome: Phần Mềm Theo Dõi Độ Tập Trung - Google... | 4.2 phút
2 giờ trước          | Code                                               | 57.5 phút

--- THỐNG KÊ ---
Tổng số task/task nhóm sau khi xử lý: 2
Thời gian trung bình mỗi task/nhóm: 30.6 phút (1851 giây)
```
