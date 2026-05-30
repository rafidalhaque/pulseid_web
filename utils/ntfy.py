import httpx, os, secrets, base64
from config import ntfy_base, ntfy_admin_token

def provision_ntfy_user(employee_id: str) -> tuple[str, str]:
    topic = f"pulseid-{secrets.token_hex(12)}"
    password = secrets.token_hex(16)
    employee_id = str(employee_id)

    username = "emp_" + employee_id[24:]

    # user creation
    httpx.put(
        f"{ntfy_base}/v1/users",
        json={"username": username, "password": password},
        headers={"Authorization": f"Bearer {ntfy_admin_token}"},
        timeout=10,
    )

    # grant read only access to their topic
    httpx.put(
        f"{ntfy_base}/v1/users/access",
        json={"username": username, "topic": topic, "permission": "ro"},
        headers={"Authorization": f"Bearer {ntfy_admin_token}"},
        timeout=10,
    )

    # generate token for android
    userpass = f"{username}:{password}"
    response = httpx.post(
        f"{ntfy_base}/v1/account/token",
        headers={"Authorization": f"Basic {base64.b64encode(userpass.encode()).decode()}"},
        timeout=10,
    )
    token = response.json().get("token")
    return topic, token

def send_notification(topic: str, title: str, message: str, priority: str, click_url: str = None):
    if not all([topic, title, message, priority]):
        return "Missing parameters"

    headers = {
        "Authorization": f"Bearer {ntfy_admin_token}",
        "Content-Type": "text/plain",
        "Title": title,
        "Priority": priority
    }
    if click_url:
        headers["Click"] = click_url

    try:
        httpx.post(f"{ntfy_base}/{topic}", content=message, headers=headers, timeout=10)
    except Exception as e:
        return f"Failed to send notification: {e}"