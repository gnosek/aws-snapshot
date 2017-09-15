# MongoDB AWS Backup and Restore

# Overview

The tooling provided here performs backups and restores of mongodb at the EBS snapshot (ie: filesystem) level.

# Backup
The overall procedure of how to backup is documented by mongodb under [Back Up a Sharded Cluster with File System Snapshots](https://docs.mongodb.com/manual/tutorial/backup-sharded-cluster-with-filesystem-snapshots/).

Backups using `mongodb-snapshot` can be run at any time, against any mongodb shard or replicationset endpoint. It is assumed that each mongodb server (in the cluster/replset) is an AWS instance and will do a lookup of the server's ip against EC2 to determine the associated ec2 instance & volumes. If the instance/volume cannot be found the backup will fail.


## mongodb-snapshot
The provided backup tooling logic is heavily lifted from [Percona labs mongodb-consistent-backup](https://github.com/Percona-Lab/mongodb_consistent_backup). Only the required code to operate to perform AWS backups has been retained and the underlying Backup class has been implemented as `AwsSnapshot` (was: `Mongodump`).

Note: The `mongodb-snapshot` tool provided in this repo is not compatible with mongodb-consistent-backup, though the config should be. It is my hope that future versions of mongodb-consistent-backup natively support AWS snapshots.

### mongodb-snapshot Overview

* Connect to provided endpoint
* Determine type of endpoint
   * If sharded: Add all replicasets in shard config
   * If replicaset: Add single replicaset
* Foreach replicaset:
    * Select suitable secondary member (see `replication.*` options for thresholds)
    * Resolves member URI -> IP -> EC2 instance
    * Foreach volume attached to EC2 instance
         * if `backup.skip_root` and root volume: ignore
         * Add volume information to backup set
* Backup pre:
    * If sharded: Stop balancer
* Backup:
    * Foreach volume in backup set: AWS EC2 [CreateSnapshot](http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateSnapshot.html)
* Backup post:
    * If sharded: Start balancer
    * Foreach volume: AWS EC2 [CreateTags](http://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateTags.html)
* Disconnect/cleanup

All tags from each source volume are copied to the destination snapshot. Additionally the following are added:

* `Backup:Replset` Replicaset associated with Host
* `Backup:Host` Host portion of URI for selected member
* `Backup:Instance` EC2 Instance ID of volume attachment
* `Backup:Device` Device of volume attachment
* `Backup:Time` Backup time internal from `mongodb-snapshot`. Format: `%Y%m%d_%H%M`, eg: `20170804_1000`.

Note: `Backup:Time` will be consistent across all snapshots from a single `mongodb-snapshot` execution.

### Usage/Config
Backups can be entirely run from the command line. Usage:

```
usage: mongodb-snapshot [-h] [-c CONFIGPATH]
                        [-e {production,staging,development}] [-v] [-H HOST]
                        [-P PORT] [-u USERNAME] [-p PASSWORD] [-a AUTHDB]
                        [-A AUTHMECH] [-s] [-I SSL_CERTFILE] [-K SSL_KEYFILE]
                        [-C SSL_CA_CERTS] [-L LOG_DIR] [--lock-file LOCK_FILE]
                        [--sharding.balancer.wait_secs SHARDING.BALANCER.WAIT_SECS]
                        [--sharding.balancer.ping_secs SHARDING.BALANCER.PING_SECS]
                        [-n NAME] [--backup.tag_prefix PREFIX]
                        [--backup.no_skip_root] [--backup.skip_root]
                        [--aws.region REGION]
                        [--aws.access_key AWS_ACCESS_KEY_ID]
                        [--aws.secret_key AWS_SECRET_ACCESS_KEY]
                        [--replication.max_lag_secs REPLICATION.MAX_LAG_SECS]
                        [--replication.min_priority REPLICATION.MIN_PRIORITY]
                        [--replication.max_priority REPLICATION.MAX_PRIORITY]
                        [--replication.hidden_only]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIGPATH, --config CONFIGPATH
                        Configuration file or directory containing the
                        configuration files.
  -e {production,staging,development}, --environment {production,staging,development}
                        The environment used for configuration. (default:
                        production)
  -v, --verbose         Verbose output
  -H HOST, --host HOST  MongoDB Hostname, IP address or
                        '<replset>/<host:port>,<host:port>,..' URI (default:
                        localhost)
  -P PORT, --port PORT  MongoDB Port (default: 27017)
  -u USERNAME, --user USERNAME, --username USERNAME
                        MongoDB Authentication Username (for optional auth)
  -p PASSWORD, --password PASSWORD
                        MongoDB Authentication Password (for optional auth)
  -a AUTHDB, --authdb AUTHDB
                        MongoDB Auth Database (for optional auth - default:
                        admin)
  -A AUTHMECH, --authmech AUTHMECH
                        MongoDB Auth Mechanism (for optional auth - default:
                        SCRAM-SHA-1)
  -s, --ssl             Create the connection to the MongoDB server using SSL
                        (default: False)
  -I SSL_CERTFILE, --ssl-certfile SSL_CERTFILE
                        The certificate file used to identify against the
                        MongoDB server
  -K SSL_KEYFILE, --ssl-keyfile SSL_KEYFILE
                        The private keyfile used to identify against the
                        MongoDB server (if different from certfile)
  -C SSL_CA_CERTS, --ssl-ca-certs SSL_CA_CERTS
                        The root certificate chain file from the Certificate
                        Authority
  -L LOG_DIR, --log-dir LOG_DIR
                        Path to write log files to (default: disabled)
  --lock-file LOCK_FILE
                        Location of lock file (default: /tmp/mongodb-
                        snapshot.lock)
  --sharding.balancer.wait_secs SHARDING.BALANCER.WAIT_SECS
                        Maximum time to wait for balancer to stop, in seconds
                        (default: 300)
  --sharding.balancer.ping_secs SHARDING.BALANCER.PING_SECS
                        Interval to check balancer state, in seconds (default:
                        3)
  -n NAME, --backup.name NAME
                        Name of the backup set (required)
  --backup.tag_prefix PREFIX
                        Prefix to add to AWS Tags (default: 'Backup:')
  --backup.no_skip_root
                        Do not skip snapshot of root volume
  --backup.skip_root    Skip snapshot of root volume (default: True)
  --aws.region REGION   AWS Region
  --aws.access_key AWS_ACCESS_KEY_ID
                        AWS Access Key
  --aws.secret_key AWS_SECRET_ACCESS_KEY
                        AWS Secret Key
  --replication.max_lag_secs REPLICATION.MAX_LAG_SECS
                        Max lag of backup replica(s) in seconds (default: 10)
  --replication.min_priority REPLICATION.MIN_PRIORITY
                        Min priority of secondary members for backup (default:
                        0)
  --replication.max_priority REPLICATION.MAX_PRIORITY
                        Max priority of secondary members for backup (default:
                        1000)
  --replication.hidden_only
                        Only use hidden secondary members for backup (default:
                        false)
```

Each argument maps through to a configuration option to make future executions simple. Example configuration can be found under `conf/example.yaml`

### Permissions

The invoker of `mongodb-backup` needs the following AWS permissions:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeSnapshots",
        "ec2:DescribeVolumes",
        "ec2:CreateSnapshot"
      ],
      "Resource": [
        "*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags"
      ],
      "Resource": "arn:aws:ec2:*::snapshot/*"
    }
  ]
}
```
AWS credentials can be provided by any of the standard [boto credential mechanisms](http://boto.cloudhackers.com/en/latest/boto_config_tut.html#credentials).

The mongodb backup user requires the following [mongodb roles](https://docs.mongodb.com/manual/reference/built-in-roles/):

```
{ role: "clusterMonitor", db: "admin" }
```
