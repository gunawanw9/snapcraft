# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import tarfile
from unittest import mock

import fixtures

from snapcraft import (
    common,
    tests,
)
from snapcraft.commands import cleanbuild


class CleanBuildCommandTestCase(tests.TestCase):

    yaml_template = """name: snap-test
version: 1.0
summary: test strip
description: if snap is succesful a snap package will be available
architectures: ['amd64']

parts:
    part1:
      plugin: nil
"""

    def make_snapcraft_yaml(self, n=1):
        super().make_snapcraft_yaml(self.yaml_template)
        self.state_file = os.path.join(common.get_partsdir(), 'part1', 'state')

    @mock.patch('snapcraft.lxd.check_call')
    @mock.patch('snapcraft.repo.is_package_installed')
    def test_cleanbuild(self, mock_installed, mock_call):
        mock_installed.return_value = True

        fake_logger = fixtures.FakeLogger(level=logging.INFO)
        self.useFixture(fake_logger)

        self.make_snapcraft_yaml()
        # simulate build artifacts

        dirs = [
            os.path.join(common.get_partsdir(), 'part1', 'src'),
            common.get_stagedir(),
            common.get_snapdir(),
            os.path.join(common.get_partsdir(), 'plugins'),
        ]
        files_tar = [
            os.path.join(common.get_partsdir(), 'plugins', 'x-plugin.py'),
            'main.c',
        ]
        files_no_tar = [
            os.path.join(common.get_stagedir(), 'binary'),
            os.path.join(common.get_snapdir(), 'binary'),
            'snap-test.snap',
            'snap-test_1.0_source.tar.bz2',
        ]
        for d in dirs:
            os.makedirs(d)
        for f in files_tar + files_no_tar:
            open(f, 'w').close()

        cleanbuild.main()

        self.assertEqual(
            'Setting up container with project assets\n'
            'Waiting for a network connection...\n'
            'Network connection established\n'
            'Retrieved snap-test_1.0_amd64.snap\n',
            fake_logger.output)

        with tarfile.open('snap-test_1.0_source.tar.bz2') as tar:
            tar_members = tar.getnames()

        for f in files_no_tar:
            f = os.path.relpath(f)
            self.assertFalse('./{}'.format(f) in tar_members,
                             '{} should not be in {}'.format(f, tar_members))
        for f in files_tar:
            f = os.path.relpath(f)
            self.assertTrue('./{}'.format(f) in tar_members,
                            '{} should be in {}'.format(f, tar_members))

    @mock.patch('snapcraft.repo.is_package_installed')
    def test_no_lxd(self, mock_installed):
        mock_installed.return_value = False
        with self.assertRaises(EnvironmentError) as raised:
            cleanbuild.main()

        self.assertEqual(
            str(raised.exception),
            'The lxd package is not installed, in order to use `cleanbuild` '
            'you must install lxd onto your system. Refer to the '
            '"Ubuntu Desktop and Ubuntu Server" section on '
            'https://linuxcontainers.org/lxd/getting-started-cli/'
            '#ubuntu-desktop-and-ubuntu-server to enable a proper setup.')