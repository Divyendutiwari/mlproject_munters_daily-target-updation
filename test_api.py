import requests

try:
    # 1. Check if the page loads
    r1 = requests.get('http://127.0.0.1:5000/')
    print("GET / :", r1.status_code)
    
    # 2. Get the schedule to find a panel_id
    r2 = requests.get('http://127.0.0.1:5000/api/schedule')
    schedule = r2.json()
    first_machine = list(schedule.keys())[0]
    first_panel = None
    for entry in schedule[first_machine]["schedule"]:
        if entry["type"] == "production":
            first_panel = entry["panel_id"]
            break
            
    print("Found panel to mark complete:", first_panel)
    
    # 3. Mark it complete
    r3 = requests.post('http://127.0.0.1:5000/api/mark_completed', json={"panel_id": first_panel})
    print("POST /api/mark_completed:", r3.status_code, r3.json())
    
    # 4. Reschedule
    r4 = requests.post('http://127.0.0.1:5000/api/reschedule')
    print("POST /api/reschedule:", r4.status_code)
    print("Scheduled panels after redistribute:", r4.json()["summary"]["total_panels_scheduled"])
    
except Exception as e:
    print("ERROR:", e)
