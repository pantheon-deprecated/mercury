import httplib
import subprocess
import datetime
import json
import time
import pprint

CERTIFICATE = "/etc/pantheon/system.pem"
API_SERVER = "api.getpantheon.com"

connection = httplib.HTTPSConnection(
    API_SERVER,
    8443,
    key_file = CERTIFICATE,
    cert_file = CERTIFICATE
)

now = time.time()

def get_nearest_hour(unix_timestamp):
    return unix_timestamp - (unix_timestamp % 3600)

def set_batch_usage(batch_post):
    body = json.dumps(batch_post)
    connection.request("POST", "/sites/self/usage/", body)
    complete_response = connection.getresponse()
    # Read the response to allow subsequent requests.
    complete_response.read()
    if complete_response.status != 200:
        raise Exception('Could not set usage.')


def set_bandwith():
    command = ["/usr/bin/vnstat", "--hours", "--dumpdb"]
    lines = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0].split("\n")
    batch_post = []
    for line in lines:
        # Ignore blank or non-hour lines.
        if line == "" or not line.startswith("h;"):
            continue
        parts = line.split(";")
        hour = get_nearest_hour(int(parts[2]))

        # Ignore data that's younger than an hour or older than an hour and a day.
        if (now - hour) <= 3600 or (now - hour) > (86400 + 3600) or hour == 0:
            continue
        inbound_kib = parts[3]
        outbound_kib = parts[4]

        stamp = datetime.datetime.utcfromtimestamp(hour)
        print("[Bandwidth] [%s] %s/%s" % (stamp.strftime("%Y-%m-%d %H:%M:%S"), inbound_kib, outbound_kib))

        batch_post.append({"metric": "bandwidth_in",
                           "start": hour,
                           "duration": 3600,
                           "amount": inbound_kib})
        batch_post.append({"metric": "bandwidth_out",
                           "start": hour,
                           "duration": 3600,
                           "amount": outbound_kib})
    set_batch_usage(batch_post)


set_bandwith()
