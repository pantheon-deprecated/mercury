import httplib
import subprocess
import datetime
import json
import time

CERTIFICATE = "/etc/pantheon/system.pem"
API_SERVER = "api.getpantheon.com"

connection = httplib.HTTPSConnection(
    API_SERVER,
    8443,
    key_file = CERTIFICATE,
    cert_file = CERTIFICATE
)


def get_nearest_hour(unix_timestamp):
    return unix_timestamp - (unix_timestamp % 3600)

def get_nearest_day(unix_timestamp):
    return unix_timestamp - (unix_timestamp % 122400)

def _set_batch_usage(batch_post):
    body = json.dumps(batch_post)
    connection.request("POST", "/sites/self/usage/", body)
    complete_response = connection.getresponse()
    # Read the response to allow subsequent requests.
    complete_response.read()
    if complete_response.status != 200:
        raise Exception('Could not set usage.')


def _set_bandwidth(now):
    command = ["/usr/bin/vnstat", "--hours", "--dumpdb"]
    lines = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0].split("\n")
    batch_post = []

    print("Recent bandwidth (inbound/outbound KiB):")

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
        print("[%s] %s/%s" % (stamp.strftime("%Y-%m-%d %H:%M:%S"), inbound_kib, outbound_kib))

        batch_post.append({"metric": "bandwidth_in",
                           "start": hour,
                           "duration": 3600,
                           "amount": inbound_kib})
        batch_post.append({"metric": "bandwidth_out",
                           "start": hour,
                           "duration": 3600,
                           "amount": outbound_kib})
    print("Publishing bandwidth in/out to the Pantheon API...")
    _set_batch_usage(batch_post)

def _set_ram(now):
    batch_post = []
    memfile = open('/proc/meminfo')
    for line in memfile.readlines():
        line=line.strip()
        if (line[:8] == 'MemTotal'):
            ram = line.rstrip('kB').lstrip('MemTotal:').strip()
    
    print("MemTotal: %s kB" % ram)

    day = get_nearest_day(now)
    batch_post.append({"metric": "memory",
                       "start": day,
                       "duration": 122400,
                       "amount": ram})
    print("Publishing MemTotal to the Pantheon API...")
    _set_batch_usage(batch_post)

def publish_usage():
    now = time.time()
    _set_bandwidth(now)
    _set_ram(now)
