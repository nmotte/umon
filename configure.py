from optparse import OptionParser
from time import gmtime, strftime
import json, uuid, os, logging
import subprocess, sys, time
from subprocess import call

def subprocess_cmd(user, host, command, timeout):
    flag=True
    while (flag):
        ssh = subprocess.Popen('ssh -o "StrictHostKeyChecking no" -o ConnectTimeout={2} {0}@{1} '.format(user, host, timeout) + command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        error = ssh.stderr.readlines()
        logging.debug(error)
        if (len(error) > 0):
            if (error[0].find('Connection timed out') == -1 and error[0].find('Could not resolve') == -1):
                flag=False
            else:
                tmp = raw_input("> {0} is unreachable, retry? [Y/N]: ".format(host))
                if (tmp == 'N'):
                    flag=False
                    return 1
        else:
            flag=False
    return 0

def main():

    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-c", "--conf",  help="Path to a configuration file", dest="conf")
    parser.add_option("-u", "--user",  help="User used for SSH and scp", dest="user")
    parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False, help="Enable debug logs")
    parser.add_option("-t", "--timeout",  help="SSH connection timeout (in seconds), default=60", dest="timeout", type="int", default=60)
    (options, args) = parser.parse_args()

    # Logging configuration
    level = logging.INFO
    if (options.debug):
        level = logging.DEBUG
    logging.basicConfig(stream=sys.stdout, level=level, format='%(levelname)s\t# %(message)s')

    if not options.conf:
        logging.info('Conf file is missing')
        parser.print_help()
        return
    if not options.user:
        logging.info('User is missing')
        parser.print_help()
        return

    with open(options.conf) as conf_file:    
        conf = json.load(conf_file)

    call(['sudo', 'yum', 'install', '-y', 'gnuplot'])

    # Install iostat and dstat
    for server in conf['servers']:
        logging.info(("Installing dstat and iostat on {0}").format(server['hostname']))
        COMMAND=('\'python -mplatform | grep -qi Ubuntu && sudo apt-get install -y sysstat dstat || sudo yum install -y sysstat dstat\'')
        subprocess_cmd(options.user, server['hostname'], COMMAND, options.timeout)
            
if __name__ == "__main__":
    main()
