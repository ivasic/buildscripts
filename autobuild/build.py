#!/usr/bin/python
# build.py
import ConfigParser

import os
import re
import subprocess
import logging
import optparse


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')


def main():
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage)
	parser.add_option("-d", "--dir", dest="dir",
	                  help="Change Xcode project directory.")

	parser.add_option("-c", "--conf", dest="conf",
	                  default='default',
	                  help="Build configuration section in your build.config file. It's 'default' by default")

	options, args = parser.parse_args()

	config_file_path = os.getcwd() + '/build.config'
	print '*** Using config file %s' % config_file_path

	if options.dir:
		print '*** Changing directory to %s' % options.dir
	else:
		os.chdir('../')

	conf = options.conf

	cp = ConfigParser.RawConfigParser()
	cp.read(config_file_path)

	targets = cp.get(conf, 'TARGETS')
	targets_args = ''
	if targets == 'ALL_TARGETS':
		targets = all_targets()
		targets_args = ''
	else:
		targets = map(str.strip, targets.split(','))
		targets_args = ''
		for t in targets:
			targets_args += '-target {0} '.format(t)

	build_scheme = cp.get(conf, 'BUILD_SCHEME')
	build_dir = 'build/{0}-iphoneos/'.format(build_scheme)
	signing_identity = cp.get(conf, 'CODE_SIGN_IDENTITY')
	provision_file = '{0}/autobuild/{1}'.format(os.getcwd(), cp.get(conf, 'PROVISIONING_PROFILE'))

	#GO BUILD
	print '*** Building... '
	rc, out = call_command('xcodebuild -configuration {0} {1}'.format(build_scheme, targets_args))
	if rc is not 0:
		print '*** Error building targets:'
		for s in out:
			print s
		exit(rc)

	print '*** BUILD SUCCEEDED ***'

	#GO IPA
	#'xcrun -sdk iphoneos PackageApplication -v "${PROJECT_BUILDDIR}/${PRODUCT_NAME}.app" -o "${BUILD_HISTORY_DIR}/${PRODUCT_NAME}.ipa"
	# --sign "${CODE_SIGN_IDENTITY}" --embed "${PROVISIONING_PROFILE}"'

	files = os.listdir(build_dir)
	for file in files:
		if not file.endswith('.app'):
			continue

		app_path = '{0}/{1}{2}'.format(os.getcwd(), build_dir, file)
		out_path = '{0}/build/{1}.ipa'.format(os.getcwd(), file)
		sign_id = '{0}'.format(signing_identity)
		prov_file = '{0}'.format(provision_file)
		rc, out = call_command_wargs('xcrun', ['-sdk', 'iphoneos', 'PackageApplication', '-v', app_path, '-o', out_path, '--sign', sign_id, '--embed', prov_file])
		if rc is 0:
			print '*** Built IPA for %s' % file
		else:
			print '*** Error building IPA for target %s' % file
			for s in out:
				print s
			exit(rc)


def all_targets():
	project_list = call_command('xcodebuild -list')[0].split('\n')
	process = False
	targets = []
	for line in project_list:
		if line.__contains__('Targets:'):
			process = True
			continue

		if process:
			if not line:
				process = False
				break

			targets.append(line.strip())
			continue

	return targets


def call_command(command):
	c = command.split(' ')
	return call_command_wargs(c[0], c[1:])

def call_command_wargs(command, args):
	c = [command]
	c.extend(args)
	process = subprocess.Popen(c,
	                           stdout=subprocess.PIPE,
	                           stderr=subprocess.PIPE)
	output = process.communicate()
	return process.returncode, output

if __name__ == "__main__":
	main()