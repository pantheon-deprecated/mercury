# Running it in the foreground

twistd -ny replication_bridge.py

# Exercising it

curl -XPUT http://localhost:9999/one/two
