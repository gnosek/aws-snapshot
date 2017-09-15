# AWS Snapshot tools

## AWS EBS Snapshot

`aws-snapshot` takes snapshots of AWS EBS volumes given one of:

* volume-id
* instance-id (all attached volumes on instance)
* device name on instance-id

```
$ aws-snapshot -h
usage: aws-snapshot [-h] [-r REGION] [-n NAME] [-k] [-w]
                    [-l {CRITICAL,FATAL,ERROR,WARN,WARNING,INFO,DEBUG,NOTSET}]
                    {device,instance,volume} ...

positional arguments:
  {device,instance,volume}
                        sub-command help
    device              Snapshot a specific device
    instance            Snapshot all attached ebs volumes on a specific
                        instance
    volume              Snapshot a specific volume

optional arguments:
  -h, --help            show this help message and exit
  -r REGION, --region REGION
                        The AWS Region to use, e.g. us-east-1/us-west-2
  -n NAME, --name NAME  The name of the ebs volume or instance. Defaults to
                        the current host.
  -k, --keep            Flag the backup to be kept (Backup:Retain)
  -w, --wait            Wait for EBS backup to complete before returning
  -l {CRITICAL,FATAL,ERROR,WARN,WARNING,INFO,DEBUG,NOTSET}, --log {CRITICAL,FATAL,ERROR,WARN,WARNING,INFO,DEBUG,NOTSET}
                        the loglevel sets the amount of output you want
```

Sub-commands:

```
$ aws-snapshot volume -h
usage: aws-snapshot volume [-h] -v VOLUMEID

optional arguments:
  -h, --help            show this help message and exit
  -v VOLUMEID, --volumeid VOLUMEID
                        The AWS VolumeId, e.g. vol-1223456
```

```
# Usage: aws-snapshot instance
$ aws-snapshot instance -h
usage: aws-snapshot instance [-h] -i INSTANCEID

optional arguments:
  -h, --help            show this help message and exit
  -i INSTANCEID, --instance-id INSTANCEID
                        The AWS InstanceId, e.g i-1223456
```

```
$ aws-snapshot device -h
usage: aws-snapshot device [-h] -d DEVICE -i INSTANCEID

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        The filesystem device name, e.g /dev/sdj
  -i INSTANCEID, --instance-id INSTANCEID
                        The AWS InstanceId, e.g i-1223456
```

### Permissions
The minimum required permissions to execute depend on how the program is called, but the full set is:

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

## AWS EBS Snapshot cleaner

Deletes all snapshots with older than specified TTL, exluding any with tag 'Backup:Retain'.

```
$ aws-snapshot-cleaner -h
usage: aws-snapshot-cleaner [-h]
                            [-l {CRITICAL,FATAL,ERROR,WARN,WARNING,INFO,DEBUG,NOTSET}]
                            [-n] [-t TTL] [--tag-key TAG_KEY]
                            [--tag-value TAG_VALUE]

optional arguments:
  -h, --help            show this help message and exit
  -l {CRITICAL,FATAL,ERROR,WARN,WARNING,INFO,DEBUG,NOTSET}, --log {CRITICAL,FATAL,ERROR,WARN,WARNING,INFO,DEBUG,NOTSET}
                        the loglevel sets the amount of output you want
  -n, --dry-run         Dry run. Do everything but deleting snapshots
  -t TTL, --ttl TTL     The time that the snapshot should stick around. The
                        following are valid: 1s, 1 second(s), 5M, 5 minute(s),
                        1H, 2 hour(s), 1d, 2 day(s), 1w, 1 week(s), 2m, 2
                        months(s), 1y, 2 year(s),
  --tag-key TAG_KEY     AWS tag key to filter on before cleaning. Can be
                        combined with tag-value for key=value, otherwise
                        independent
  --tag-value TAG_VALUE
                        AWS tag value to filter on before cleaning. Can be
                        combined with tag-key for key=value, otherwise
                        independent
```

### Permissions
Required permissions to execute:

	{
		"Version": "2012-10-17",
		"Statement": [
			{
				"Effect": "Allow",
				"Action": [
					"ec2:DescribeSnapshots",
					"ec2:DeleteSnapshot"
				],
				"Resource": [
					"*"
				]
			},
			{
				"Effect": "Allow",
				"Action": [
					"logs:CreateLogGroup",
					"logs:CreateLogStream",
					"logs:PutLogEvents"
				],
				"Resource": "arn:aws:logs:*:*:*"
			}
		]
	}

### Lambda deployment
`aws-snapshot-cleaner` can be scheduled and executed via lambda. To install:

* Build: `./build.sh`
* Upload `dist.zip` to S3
* Deploy cloudformation.yaml
* Tag instances
