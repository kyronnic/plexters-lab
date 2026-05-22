from plexter.notifications import notify_info, notify_success, notify_failure

notify_info("Plexter notification test: info")
notify_success("Plexter notification test: success")
notify_failure("Plexter notification test: failure")

print("Notification test complete.")