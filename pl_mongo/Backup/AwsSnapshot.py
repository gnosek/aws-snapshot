import os
import logging

import boto.ec2

from socket import gethostbyname
from os.path import isfile

from boto.exception import BotoServerError
from boto.utils import get_instance_identity

from pl_mongo.Errors import Error, OperationError
from pl_mongo.Task import Task

def looks_like_ec2():
    if isfile('/sys/hypervisor/uuid'):
        with open('/sys/hypervisor/uuid') as hvm_uuid:
            if hvm_uuid.read(3) == 'ec2':
                return True
    return False

class AwsSnapshotInstance(object):
    def __init__(self, config, backup_time, boto_conn, host, replset):
        self.backup_time = backup_time
        self.boto_conn   = boto_conn
        self.host        = host
        self.replset     = replset
        self.backup_name = config.backup.name
        self.tag_prefix  = config.backup.tag_prefix
        self.skip_root   = config.backup.skip_root

        self.host_ip    = gethostbyname(host)
        self.instance   = None
        self.volumes    = {}
        self.snapshots  = {}

        self.get_instance()
        self.get_volumes()

    def get_instance(self):
        if not self.instance:
            logging.debug("Finding instance associated with %s ip: %s" % (self.host, self.host_ip))
            instances = self.boto_conn.get_only_instances(
                filters={ 'private-ip-address': self.host_ip }
            )

            if len(instances) == 0:
                raise OperationError("Could not find any instances associated with ip: %s" % self.host_ip)
            elif len(instances) > 1: # This should never happen
                raise OperationError("Found too many instances associated with ip: %s" % self.host_ip)

            self.instance = instances[0]
            logging.info("Instance associated with %s: %s" % (self.host, self.instance))
        return self.instance

    def get_volumes(self):
        for dev, mapping in self.instance.block_device_mapping.items():
            if self.skip_root and dev == '/dev/sda1':
                logging.info("Skipping instance %s root volume %s" % (self.instance.id, dev))
                continue

            try:
                logging.info("Getting volume information for %s %s: %s" % (self.instance.id, dev, mapping.volume_id))
                volumes = self.boto_conn.get_all_volumes(mapping.volume_id)
                self.volumes[dev] = volumes[0]
            except BotoServerError:
                raise OperationError("Could not get volume information for: %s" % mapping.volume_id)

    def add_snapshot_tag(self, dev, tag_key, tag_value, prefix=True):
        try:
            snapshot = self.snapshots[dev]

            if prefix:
                tag_key = self.tag_prefix + tag_key
            if tag_key.startswith('aws:'):
                logging.warn("Unable to snapshot %s with tag %s: reserved namespace. Prefixing with %s instead." % (snapshot.id, tag_key, self.tag_prefix))
                tag_key = self.tag_prefix + tag_key

            logging.info("Adding snapshot %s tag %s=%s" % (snapshot.id, tag_key, tag_value))
            snapshot.add_tag(tag_key, value=tag_value)
        except KeyError:
            raise OperationError("No snapshot found for device %s" % dev)

    def run(self):
        for dev, volume in self.volumes.items():
            # mongodb-snapshot csRS/cfg01.blah.com i-10127747238:/dev/xvdf 2017-08-04 14:07:47.237650
            description = "mongodb-snapshot %s %s/%s %s:%s %s" % (
                self.backup_name,
                self.replset, self.host,
                self.instance.id, dev,
                self.backup_time
            )

            logging.info("Creating snapshot for %s: %s" % (volume.id, description))
            snapshot = self.boto_conn.create_snapshot(volume.id, description)
            self.snapshots[dev] = snapshot
            logging.info("Snapshot created for for %s: %s" % (volume.id, snapshot))

            self.add_snapshot_tag(dev, 'Replset', self.replset)
            self.add_snapshot_tag(dev, 'Host', self.host)
            self.add_snapshot_tag(dev, 'Instance', self.instance.id)
            self.add_snapshot_tag(dev, 'Device', dev)
            self.add_snapshot_tag(dev, 'Time', self.backup_time)
            for tag_key, tag_value in volume.tags.items():
                self.add_snapshot_tag(dev, tag_key, tag_value, prefix=False)


class AwsSnapshot(Task):
    def __init__(self, manager, config, timer, replsets, backup_time, backup_stop=None, sharding=None):
        super(AwsSnapshot, self).__init__(self.__class__.__name__, manager, config, timer)
        self.backup_time        = backup_time
        self.replsets           = replsets
        self.backup_stop        = backup_stop
        self.sharding           = sharding

        self.region_name           = config.aws.region
        self.aws_access_key_id     = config.aws.access_key
        self.aws_secret_access_key = config.aws.secret_key

        self.parts              = {}
        self.region             = None
        self.boto_conn          = None

        self.get_region()
        self.aws_connect()
        self.get_instances()

    def get_region(self):
        # get from environment
        if self.region_name is None:
            self.region_name = os.environ.get('AWS_DEFAULT_REGION', None)
        if self.region_name is None:
            self.region_name = os.environ.get('AWS_REGION', None)
        # Attempt instance metadata
        if self.region_name is None and looks_like_ec2():
            identity = get_instance_identity()
            self.region_name = identity['document']['region']

        if self.region_name is None:
            raise OperationError("aws.region unset, and could not be determined from environment")

        self.region = boto.ec2.get_region(self.region_name)

    def aws_connect(self):
        self.boto_conn = boto.ec2.connection.EC2Connection(
            region=self.region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )
        logging.info("Connection made to AWS: %s" % self.boto_conn)

    def get_instances(self):
        # backup a secondary from each shard
        for shard in self.replsets:
            secondary = self.replsets[shard].find_secondary()
            for mongo_addr in secondary['uri'].addrs:
                logging.info("Adding AWS Instance Snapshot for %s: %s" % (shard, mongo_addr.host))
                self.parts[shard] = AwsSnapshotInstance(
                    self.config,
                    self.backup_time,
                    self.boto_conn,
                    mongo_addr.host,
                    shard,
                )

        # backup a single sccc/non-replset config server, if exists:
        if self.sharding:
            config_server = self.sharding.get_config_server()
            if config_server and isinstance(config_server, dict):
                logging.info("Using non-replset backup method for configsvr: %s" % (config_server['host']))
                self.parts['configsvr'] = AwsSnapshotInstance(
                    self.config,
                    self.backup_time,
                    self.boto_conn,
                    config_server['host'],
                    'configsvr',
                )

    def run(self):
        self.timer.start(self.timer_name)
        self.running = True

        for part in self.parts.values():
            part.run()

        self.timer.stop(self.timer_name)
        self.running = False
        self.stopped = True
        self.completed = True

    def close(self):
        self.boto_conn.close()
