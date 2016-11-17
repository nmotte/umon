from optparse import OptionParser
from time import gmtime, strftime
import json, uuid, os, logging
import subprocess, sys, time
from subprocess import call

def subprocess_cmd(user, host, command, timeout, identity):
    flag=True
    while (flag):
        ssh = subprocess.Popen('ssh -o "StrictHostKeyChecking no" -o ConnectTimeout={2} -i {3} {0}@{1} '.format(user, host, timeout, identity) + command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    parser.add_option("-u", "--user",     help="User used for SSH and scp", dest="user")
    parser.add_option("-i", "--identity-file",     help="Identity-file used for SSH and scp", dest="identity")
    parser.add_option("-r", "--runtime",  help="Monitoring time (in seconds), default=-1 (stops on user input)", dest="time", type="int", default=-1)
    parser.add_option("-j", "--json-conf",     help="Path to a configuration file", dest="conf")
    parser.add_option("-s", "--sampling", help="Sampling time (time between two dots, in seconds), default=5", dest="sampling", type="int", default=5)
    parser.add_option("-t", "--timeout",  help="SSH connection timeout (in seconds), default=60", dest="timeout", type="int", default=60)
    parser.add_option("-c", "--clean-up", action="store_true", dest="clean", default=False, help="Clean up all running processes and files on all servers")
    parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False, help="Enable debug logs")
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
    if not options.identity:
        logging.info('Identity file is missing')
        parser.print_help()
        return

    if (options.clean):

        with open(options.conf) as conf_file:
            conf = json.load(conf_file)

        for server in conf['servers']:
            logging.info(("Cleaning up {0}").format(server['hostname']))
            COMMAND=('\'cat *.pid | xargs --no-run-if-empty kill;'
            'rm -f *.pid;'
            'rm -f *.dat;\'')
            subprocess_cmd(options.user, server['hostname'], COMMAND, options.timeout, options.identity)

        logging.info('Clean up done, exiting now')
        sys.exit(0)

    if not options.time:
        logging.info('Monitoring time is missing')
        parser.print_help()
        return

    uid = str(uuid.uuid4())

    with open(options.conf) as conf_file:    
        conf = json.load(conf_file)

    logging.info('Umon UID: {0}'.format(uid))

    with open(".uid.{0}".format(uid), "w") as tmp:
        tmp.write(uid)

    # Start dstat
    for server in conf['servers']:
        logging.info(("Starting dstat and iostat on {0}").format(server['hostname']))
        COMMAND=('\'nohup dstat --noheaders -t -n -N {3} -d -D {1} -c -m -y --output dstat.{0}.dat {4} > /dev/null 2>&1&'
        'echo $! > dstat.{0}.pid;'
        'nohup iostat -d -x -m -p {1} {4} | awk "/{2}\ / {{printf \\"%s,%s\\n\\",\$11,\$12; fflush(stdout)}}" | awk "NR%{5}!=0 {{printf \$0;printf \\",\\";fflush(stdout)}} NR%{5}==0 {{printf \$0;print \\"\\";fflush(stdout)}}" > iostat.{0}.dat&'
        'echo $! > iostat.{0}.pid;\'').format(uid, ','.join(server['devices']), '\ |'.join(server['devices']), ','.join(server['interfaces']), options.sampling, len(server['devices']))
        subprocess_cmd(options.user, server['hostname'], COMMAND, options.timeout, options.identity)
            
    
    # Wait for test
    if ( options.time > 0):
        logging.info(("Umon started at {0} GMT, it will stop in {1} seconds...").format(strftime("%H:%M:%S", gmtime()), options.time))
        time.sleep(options.time)
    else:
        logging.info(("Umon started at {0} GMT... Enter 'stop' to stop:").format(strftime("%H:%M:%S", gmtime())))
        tmp = ''
        while (tmp != 'stop'):
            tmp = raw_input("> ")
    
    # Stop dstat
    for server in conf['servers']:
        logging.info(("Stopping dstat and iostat on {0}").format(server['hostname']))
        COMMAND=('\'kill `cat dstat.{0}.pid`;kill `cat iostat.{0}.pid`;rm -f iostat.{0}.pid dstat.{0}.pid;\'').format(uid)
        subprocess_cmd(options.user, server['hostname'], COMMAND, options.timeout, options.identity)

    # Gather stats
    for server in conf['servers']:
        logging.info("Retrieving and merging stats from {0}".format(server['hostname']))
        call('scp -o "StrictHostKeyChecking no" -o ConnectTimeout={2} -i {4} {3}@{0}:./dstat.{1}.dat ./{0}.dstat.dat > /dev/null 2>&1'.format(server['hostname'], uid, options.timeout, options.user, options.identity), shell=True)
        with open("tmpfile", "w") as tmp:
            call(['sed', '1,7d', '{0}.dstat.dat'.format(server['hostname'])], stdout=tmp)
        call(['mv', 'tmpfile', '{0}.dstat.dat'.format(server['hostname'])])
        call('scp -o "StrictHostKeyChecking no" -o ConnectTimeout={2} -i {4} {3}@{0}:./iostat.{1}.dat ./{0}.iostat.dat > /dev/null 2>&1'.format(server['hostname'], uid, options.timeout, options.user, options.identity), shell=True)
        call('paste -d "," ./{0}.dstat.dat ./{0}.iostat.dat > ./{0}.dat; rm -f ./{0}.dstat.dat ./{0}.iostat.dat'.format(server['hostname']), shell=True)
        COMMAND=("rm -f dstat.{0}.dat iostat.{0}.dat").format(uid)
        subprocess_cmd(options.user, server['hostname'], COMMAND, options.timeout, options.identity)

    call(['rm', '-f', 'umon.gnu'])
    # Create GNU Plot file
    logging.info("Generating gnuplot configuration file")
    WIDTH=900*len(conf['servers'])
    HEIGHT=800*len(conf['servers'])
    GNU_FILE=('set terminal png size {0},{1} enhanced font "Helvetica,20"\n'
     'set output "output.png"\n'
     'set datafile separator ","\n'
     'set key outside left\n'
     'set key spacing 0.5\n'
     'set style line 80 lt 0 lc rgb "#808080"\n'
     'set border 3 back ls 80 \n'
     'set style line 81 lt 0 lc rgb "#808080" lw 0.5\n'
     'set grid back ls 81\n'
     'set style line 1 lt 1 lc rgb "#A00000" lw 2 pt 7 ps 1\n'
     'set style line 2 lt 1 lc rgb "#00A000" lw 2 pt 11 ps 1\n'
     'set style line 3 lt 1 lc rgb "#5060D0" lw 2 pt 9 ps 1\n'
     'set style line 4 lt 1 lc rgb "#0000A0" lw 2 pt 8 ps 1\n'
     'set style line 5 lt 1 lc rgb "#D0D000" lw 2 pt 13 ps 1\n'
     'set style line 6 lt 1 lc rgb "#00D0D0" lw 2 pt 12 ps 1\n'
     'set style line 7 lt 1 lc rgb "#B200B2" lw 2 pt 5 ps 1\n'
     'set multiplot layout {2},6 rowsfirst title "\\n\\nhttps://github.com/nmotte/umon\\n\\n" font ",60"\n').format(WIDTH, HEIGHT, len(conf['servers']))
    
    
    for server in conf['servers']:
        GNU_FILE+=(
            # Network
            'set title "Network {0}" font ",40"\n'
            'set format y "%.0s%cB"\n'
            'plot '
        ).format(server['hostname'])

        line_style = 1
        field = 2
        interfaces = []
        for interface in server['interfaces']:
            interfaces.append(('"{0}.dat" u {1} w lp ls {2} t "Recv {5}", "{0}.dat" u {3} w lp ls {4} t "Send {5}"').format(server['hostname'], field, line_style, field+1, line_style+1, interface))
            line_style+=2
            field+=2
        GNU_FILE+=','.join(interfaces)+'\n'

        GNU_FILE+=(# IO
            'set title "IO {0}" font ",40"\n'
            'set format y "%.0s%cB"\n'
            'plot '
        ).format(server['hostname'])

        line_style = 1
        devices = []
        for device in server['devices']:
            devices.append(('"{0}.dat" u {1} w lp ls {2} t "R {3}"').format(server['hostname'], field, line_style, device))
            line_style+=1
            field+=1
            devices.append(('"{0}.dat" u {1} w lp ls {2} t "W {3}"').format(server['hostname'], field, line_style, device))
            line_style+=1
            field+=1
        GNU_FILE+=','.join(devices)+'\n'

        GNU_FILE+=(
            # CPU
            'set title "CPU {0}" font ",40"\n'
            'unset format\n'
            'plot "{0}.dat" u (${1}+${2}+${3}+${4}+${5}+${6}) w filledcurves x1 ls 1 t "usr", \\\n'
                 '"{0}.dat" u (${2}+${3}+${4}+${5}+${6}) w filledcurves x1 ls 2 t "idl", \\\n'
                 '"{0}.dat" u (${2}+${4}+${5}+${6}) w filledcurves x1 ls 3 t "sys", \\\n'
                 '"{0}.dat" u (${4}+${5}+${6}) w filledcurves x1 ls 4 t "wait", \\\n'
                 '"{0}.dat" u (${5}+${6}) w filledcurves x1 ls 5 t "hiq", \\\n'
                 '"{0}.dat" u (${6}) w filledcurves x1 ls 6 t "siq"\n'
            # Memory
            'set title "Memory {0}" font ",40"\n'
            'set format y "%.0s%cB"\n'
            'plot "{0}.dat" u (${7}+${8}+${9}+${10}) w filledcurves x1 ls 1 t "used", \\\n'
                 '"{0}.dat" u (${8}+${9}+${10}) w filledcurves x1 ls 4 t "buf", \\\n'
                 '"{0}.dat" u (${9}+${10}) w filledcurves x1 ls 3 t "cache", \\\n'
                 '"{0}.dat" u (${10}) w filledcurves x1 ls 2 t "free"\n'
            # System stats
            'set title "System stats {0}" font ",40"\n'
            'set format y "%.0s%c"\n'
            'plot "{0}.dat" u {11} w lp ls 1 t "Csw"\n'
            # w_await
            'set title "await {0}" font ",40"\n'
            'unset format\n'
            'plot '
        ).format(server['hostname'], field, field+1, field+2, field+3, field+4, field+5, field+6, field+7, field+8, field+9, field+11)
        field += 12

        line_style = 1
        devices = []
        for device in server['devices']:
            devices.append(('"{0}.dat" u {1} w lp ls {2} t "r await {3}"').format(server['hostname'], field, line_style, device))
            line_style+=1
            field+=1
            devices.append(('"{0}.dat" u {1} w lp ls {2} t "w await {3}"').format(server['hostname'], field, line_style, device))
            line_style+=1
            field+=1
        GNU_FILE+=','.join(devices)+'\n'
    
    GNU_FILE+=('unset multiplot')

    with open("umon.gnu", "w") as gnufile:
        gnufile.write(GNU_FILE)
    
    logging.info("Dumping graphs in output.png")
    call(['gnuplot', '-p', 'umon.gnu'])

    os.remove('umon.gnu')
    os.remove(".uid.{0}".format(uid))

if __name__ == "__main__":
    main()
