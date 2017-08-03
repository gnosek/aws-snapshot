import json
import pl_mongo
import sys

from argparse import Action
from pkgutil import walk_packages
from yconf import BaseConfiguration
from yconf.util import NestedDict


class ConfigParser(BaseConfiguration):
    def makeParserLoadSubmodules(self, parser):
        for _, modname, ispkg in walk_packages(path=pl_mongo.__path__, prefix=pl_mongo.__name__+'.'):
            if not ispkg:
                continue
            try:
                components = modname.split('.')
                mod = __import__(components[0])
                for comp in components[1:]:
                    mod = getattr(mod, comp)
                parser = mod.config(parser)
            except AttributeError, e:
                continue
        return parser

    def makeParser(self):
        parser = super(ConfigParser, self).makeParser()
        parser.add_argument("-v", "--verbose", dest="verbose", help="Verbose output", default=False, action="store_true")
        parser.add_argument("-H", "--host", dest="host", help="MongoDB Hostname, IP address or '<replset>/<host:port>,<host:port>,..' URI (default: %(default)s)", default="localhost", type=str)
        parser.add_argument("-P", "--port", dest="port", help="MongoDB Port (default: %(default)s)", default=27017, type=int)
        parser.add_argument("-u", "--user", "--username", dest="username", help="MongoDB Authentication Username (for optional auth)", type=str)
        parser.add_argument("-p", "--password", dest="password", help="MongoDB Authentication Password (for optional auth)", type=str)
        parser.add_argument("-a", "--authdb", dest="authdb", help="MongoDB Auth Database (for optional auth - default: %(default)s)", default='admin', type=str)
        parser.add_argument("-A", "--authmech", dest="authmech", help="MongoDB Auth Mechanism (for optional auth - default: %(default)s)", default='SCRAM-SHA-1', type=str)
        parser.add_argument("-s", "--ssl", dest="ssl", help="Create the connection to the MongoDB server using SSL (default: %(default)s)", default=False, action="store_true")
        parser.add_argument("-I", "--ssl-certfile", dest="ssl_certfile", help="The certificate file used to identify against the MongoDB server", type=str)
        parser.add_argument("-K", "--ssl-keyfile", dest="ssl_keyfile", help="The private keyfile used to identify against the MongoDB server (if different from certfile)", type=str)
        parser.add_argument("-C", "--ssl-ca-certs", dest="ssl_ca_certs", help="The root certificate chain file from the Certificate Authority", type=str)
        parser.add_argument("-L", "--log-dir", dest="log_dir", help="Path to write log files to (default: disabled)", default='', type=str)
        parser.add_argument("--lock-file", dest="lock_file", help="Location of lock file (default: %(default)s)", default='/tmp/mongodb-snapshot.lock', type=str)
        parser.add_argument("--sharding.balancer.wait_secs", dest="sharding.balancer.wait_secs", help="Maximum time to wait for balancer to stop, in seconds (default: %(default)s)", default=300, type=int)
        parser.add_argument("--sharding.balancer.ping_secs", dest="sharding.balancer.ping_secs", help="Interval to check balancer state, in seconds (default: %(default)s)", default=3, type=int)
        return self.makeParserLoadSubmodules(parser)


class Config(object):
    # noinspection PyUnusedLocal
    def __init__(self):
        self._config = ConfigParser()
        self.parse()

    def _get(self, keys, data=None):
        if not data:
            data = self._config
        if "." in keys:
            key, rest = keys.split(".", 1)
            return self._get(rest, data[key])
        else:
            return data[keys]

    def check_required(self):
        required = [
            'backup.name'
        ]
        for key in required:
            try:
                self._get(key)
            except:
                raise pl_mongo.Errors.OperationError('Field "%s" must be set via command-line or config file!' % key)

    def parse(self):
        self._config.parse(self.cmdline)
        self.check_required()

    def to_dict(self, data):
        if isinstance(data, dict) or isinstance(data, NestedDict):
            ret = {}
            for key in data:
                value = self.to_dict(data[key])
                if value and key is not ('merge'):
                    if key == "password" or key == "secret_key":
                        value = "******"
                    ret[key] = value
            return ret
        elif isinstance(data, (str, int, bool)): # or isinstance(data, int) or isinstance(data, bool):
            return data

    def dump(self):
        return self.to_dict(self._config)

    def to_json(self):
        return json.dumps(self.dump(), sort_keys=True)

    def __repr__(self):
        return self.to_json()

    def __getattr__(self, key):
        try:
            return self._config.get(key)
        # TODO-timv What can we do to make this better?
        except:
            return None
