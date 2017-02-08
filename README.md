# AWS Snapshot tools

## AWS EBS Snapshot cleaner

Deletes all snapshots with 'Backup:Expires' tag older than now.

### Build
To create a deployment package.

	./build.sh

### Install

To install:

* Build
* Upload to S3
* Deploy cloudformation.yaml
* Tag instances

### Permissions
Required role permissions:

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
