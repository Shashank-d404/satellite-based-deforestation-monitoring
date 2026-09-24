import urllib.request

URL = (
    "https://tiles.globalforestwatch.org/"
    "gfw_integrated_alerts/latest/"
    "dynamic/6/56/37.png"
)

try:
    with urllib.request.urlopen(URL, timeout=15) as response:
        data = response.read()

        print("Status code:", response.status)
        print("Content type:", response.headers.get("Content-Type"))
        print("Downloaded bytes:", len(data))

except Exception as error:
    print("Request failed:", error)