from argparse import ArgumentParser
import configparser

from .fetch import doIt
import asyncio

def main():
    """The main function for our script."""


    # Create an OptionParser to handle command-line arguments and options.

    parser = ArgumentParser()
    parser.add_argument('token', help='GRiD access token')
    parser.add_argument('-c', '--threads', dest='threads', type=int, default=4,
        help='Number of threads to use for downloads')
    parser.add_argument('-u', '--url', dest='url', default="https://grid.nga.mil/grid",
        help='GRiD Instance URL')
    parser.add_argument('-s', '--start-id', dest='start_id', default=0,
        help='Starting exportfile ID. Will ignore exportfile '
             'downloads for previous exportfiltes.'
    )

    parser.add_argument('--conf', action='append')

    parser.add_argument('-f','--force', dest='is_overwrite', default=False,
        action='store_true', help='Overwrite existing files.')
    parser.add_argument('-l', '--log', dest='log_level', default='INFO',
        help='Log level (INFO/DEBUG)')
    parser.add_argument('-d', '--dir', dest='download_dir', default='downloads',
        help='Directory to use for downloads')
    parser.add_argument('-i', '--identifier', dest='sync_flag', default='#gridsync',
        help='Flag to identify the AOI for syncing')

    # Parse the command-line arguments.
    args = parser.parse_args()

    if args.conf is not None:
        for fname in args.conf:
            with open(fname, 'r') as f:
                config = configparser.ConfigParser()
                config.read(fname)
                parser.set_defaults(**config)

    # Reload arguments to override config file values with command line values
    args = parser.parse_args()

    doIt(args)
