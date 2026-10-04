# Database
*Everything here was taken from: https://docs.pingcap.com/tidb/stable/quick-start-with-tidb/#deploy-a-local-test-cluster*

## Install TiDB
You can install TiDB on Linux using:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
source ~/.bashrc
```

## Running TiDB Test Cluster
If you need to test something (or just want to see if your install worked correctly), run:
```bash
tiup playground
```

This may fail, and prompt you to install some additional dependencies (e.x. Prometheus). Please run the command(s) you are told to run in the error message.

If you need to reset your cluster, you can run:
```bash
tiup clean playground --all
```