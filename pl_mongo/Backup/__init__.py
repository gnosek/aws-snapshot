from AwsSnapshot import AwsSnapshot

def config(parser):
    parser.add_argument("-n", "--backup.name", metavar="NAME", dest="backup.name", help="Name of the backup set (required)", type=str)
    parser.add_argument("--backup.tag_prefix", metavar="PREFIX", dest="backup.tag_prefix", help="Prefix to add to AWS Tags (default: '%(default)s')", default="Backup:", type=str)
    parser.add_argument("--backup.no_skip_root", dest="backup.skip_root", help="Do not skip snapshot of root volume", action="store_false")
    parser.add_argument("--backup.skip_root", dest="backup.skip_root", help="Skip snapshot of root volume (default: %(default)s)", default=True, action="store_true")
    parser.add_argument("--aws.region", metavar="REGION", dest="aws.region", help="AWS Region", default=None, type=str)
    parser.add_argument("--aws.access_key", metavar="AWS_ACCESS_KEY_ID", dest="aws.access_key", help="AWS Access Key", default=None, type=str)
    parser.add_argument("--aws.secret_key", metavar="AWS_SECRET_ACCESS_KEY", dest="aws.secret_key", help="AWS Secret Key", default=None, type=str)
    return parser
