#!/usr/bin/python
# build.py
import ConfigParser
import os
import shutil
import subprocess
import logging
import optparse


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

class TargetInfo():
	name = ''
	build_scheme = ''
	build_dir = ''
	code_sign_identity = ''
	provisioning_profile = ''
	archive_output_dir = ''
	build_command = ''


def main():

	targets = get_config_targets(parse_input_args())

	for target in targets:
		#GO BUILD
		print '*** Building {0}...'.format(target.name)
		rc, out = call_command(target.build_command)
		if rc is not 0:
			print '*** Error building targets:'
			for s in out:
				print s
			exit(rc)

		print '*** BUILD SUCCEEDED ***'

		files = os.listdir(target.build_dir)
		for file in files:
			if not file.endswith('.app'):
				continue

			app_path = '{0}/{1}{2}'.format(os.getcwd(), target.build_dir, file)
			out_path_dir = '{0}/{1}/'.format(target.archive_output_dir, file.replace('.app', ''))
			if not os.path.exists(out_path_dir):
				os.makedirs(out_path_dir)
			out_path = '{0}{1}.ipa'.format(out_path_dir, file.replace('.app', ''))
			sign_id = '{0}'.format(target.code_sign_identity)
			prov_file = '{0}'.format(target.provisioning_profile)
			rc, out = call_command_wargs('xcrun', ['-sdk', 'iphoneos', 'PackageApplication', '-v', app_path, '-o', out_path, '--sign', sign_id, '--embed', prov_file])
			if rc is 0:
				print '*** Built IPA for %s' % file
				process_build_dir_after_ipa(target.build_dir, out_path_dir)
			else:
				print '*** Error building IPA for target %s' % file
				for s in out:
					print s
				exit(rc)

def process_build_dir_after_ipa(build_dir, out_path_dir):
	files = os.listdir(build_dir)
	for f in files:
		if f.endswith('.app') or f.endswith('.dsym') or f.endswith('.dSYM'):
			shutil.move('{0}{1}'.format(build_dir, f), out_path_dir)

def get_config_targets(config_file_path):
	cp = ConfigParser.RawConfigParser()
	cp.read(config_file_path)

	#read targets
	targets = cp.get('default', 'TARGETS')
	if targets:
		targets = map(str.strip, targets.split(','))
	else:
		print '*** NO TARGETS DEFINED IN YOUR CONFIG FILE'
		exit(1)

	all_targets = []
	for target in targets:
		#OUT_DIR
		out_dir = cp.get(target, 'ARCHIVE_OUTPUT_DIR')
		if not out_dir:
			out_dir = '{0}/build/'.format(os.getcwd())
		if not out_dir.endswith('/'):
			out_dir += '/'
		if not os.path.exists(out_dir):
			os.makedirs(out_dir)

		build_scheme = cp.get(target, 'BUILD_SCHEME')
		build_dir = 'build/{0}-iphoneos/'.format(build_scheme)
		signing_identity = cp.get(target, 'CODE_SIGN_IDENTITY')
		provision_file = '{0}/autobuild/{1}'.format(os.getcwd(), cp.get(target, 'PROVISIONING_PROFILE'))

		ti = TargetInfo()
		ti.name = target
		ti.build_scheme = build_scheme
		ti.archive_output_dir = out_dir
		ti.code_sign_identity = signing_identity
		ti.provisioning_profile = provision_file
		ti.build_dir = build_dir
		ti.build_command = 'xcodebuild -configuration {0} -target {1}'.format(build_scheme, target)
		all_targets.append(ti)

	return all_targets

def parse_input_args():
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage)
	parser.add_option("-d", "--dir", dest="dir",
	                  help="Change Xcode project directory.")

	options, args = parser.parse_args()

	config_file_path = os.getcwd() + '/build.config'
	print '*** Using config file %s' % config_file_path

	if options.dir:
		print '*** Changing directory to %s' % options.dir
	else:
		os.chdir('../')

	return config_file_path

def list_all_targets():
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