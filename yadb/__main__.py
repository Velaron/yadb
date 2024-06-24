import argparse

import yadb
import yadb.migration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--migrate', action='store_true',
                        help='migrate config from .json to .ini')

    args = parser.parse_args()
    if args.migrate:
        yadb.migration.migrate_config()
        return

    yadb.bot.run()


if __name__ == "__main__":
    main()
