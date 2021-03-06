#!/usr/bin/python

# Copyright 2017 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import logging
import subprocess
import sys

from testsuite import deploy_app
from testsuite import test_util


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', '-d', type=str,
                        help='Directory of app to be run',
                        required=True)
    parser.add_argument('--language', '-l', type=str,
                        help='Language of the app deployed',
                        required=False)
    parser.add_argument('--verbose', '-v', help='Debug logging',
                        action='store_true', required=False)
    parser.add_argument('--skip-builders', action='store_true',
                        help='Skip runtime builder flow', default=False)
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # retrieve previous config value to reset after
    cmd = ['gcloud', 'config', 'list', '--format=json']
    output = json.loads(subprocess.check_output(cmd))
    prev_builder_value = None
    if 'app' in output:
        prev_builder_value = output.get('app').get('use_runtime_builders')

    logging.info(prev_builder_value)
    sys.exit(1)

    # disable app/use_runtime_builders to hit the XRT flow
    _set_runtime_builder_flag(False)
    _deploy_and_test(args.directory, args.language, True)

    if args.skip_builders:
        logging.info('Skipping builder flow.')
        return 0

    # set app/use_runtime_builders to explicitly enter builder flow
    _set_runtime_builder_flag(True)
    _deploy_and_test(args.directory, args.language, False)

    _set_runtime_builder_flag(prev_builder_value)


def _set_runtime_builder_flag(flag):
    try:
        if flag is None:
            cmd = ['gcloud', 'config', 'unset',
                   'app/use_runtime_builders']
        else:
            cmd = ['gcloud', 'config', 'set',
                   'app/use_runtime_builders', str(flag)]
        subprocess.check_output(cmd)
    except subprocess.CalledProcessError as cpe:
        logging.error(cpe.output)
        sys.exit(1)


def _deploy_and_test(appdir, language, is_xrt):
    version = None
    try:
        logging.debug('Testing runtime image.')
        version = deploy_app.deploy_app_and_record_latency(appdir,
                                                           language, is_xrt)
        application_url = test_util.retrieve_url_for_version(version)
        output, status_code = test_util.get(application_url)

        if status_code:
            logging.error('Application returned non-zero status code: %d',
                          status_code)
            logging.error(output)
            sys.exit(status_code)
    except Exception as e:
        logging.error('Error when contacting application!')
        logging.error(e)
    finally:
        if version:
            deploy_app.stop_app(version)


if __name__ == '__main__':
    sys.exit(main())
