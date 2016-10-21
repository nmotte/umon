from optparse import OptionParser
import json
import subprocess, sys, time
from subprocess import call

def subprocess_cmd(user, host, command):
    ssh = subprocess.Popen("ssh -o StrictHostKeyChecking=no {0}@{1} ".format(user, host) + command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = ssh.stdout.readlines()
    if result == []:
        error = ssh.stderr.readlines()
        #print >>sys.stderr, "ERROR: %s" % error
    else:
        print result

def main():

    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-t", "--time", type="int", dest="time")
    parser.add_option("-c", "--conf", dest="conf")
    (options, args) = parser.parse_args()

    if not options.time:
        print 'Time is missing'
        parser.print_help()
        return
    if not options.conf:
        print 'Conf file is missing'
        parser.print_help()
        return

    with open(options.conf) as conf_file:    
        conf = json.load(conf_file)

    # Start dstat
    for server in conf['servers']:
        print("# Starting dstat on {0}").format(server['hostname'])
        COMMAND=('\'nohup dstat --noheaders -t -n -N eth1 -d -D ' + ','.join(server['device']) + ' -c -m -y --output plot.dat 5 > /dev/null 2>&1&\''
        '\'iostat -d -x -m -p ' + ','.join(server['device']) + ' 5 | awk "/' + '\ |'.join(server['device']) + '\ / {print \$10; fflush(stdout)}" | awk "NR%2{printf \\"%s,\\",\$0;fflush(stdout);next;;}1" > iostat.dat&\'')
        subprocess_cmd("root", server['hostname'], COMMAND)
    
    # Wait for test
    print("# Monitoring for {0} seconds...").format(options.time)
    time.sleep(options.time)
    
    # Stop dstat
    for server in conf['servers']:
        print("# Stopping dstat on {0}").format(server['hostname'])
        COMMAND=('\'ps aux | grep dstat | grep plot.dat | awk "{print \$2}" | xargs kill\'')
        subprocess_cmd("root", server['hostname'], COMMAND)

    # Gather stats
    for server in conf['servers']:
        print "# Retrieving and merging stats from {0}".format(server['hostname'])
        call('scp -o "StrictHostKeyChecking no" root@{0}:./plot.dat ./{0}.dstat.dat > /dev/null 2>&1'.format(server['hostname']), shell=True)
        call('scp -o "StrictHostKeyChecking no" root@{0}:./iostat.dat ./{0}.iostat.dat > /dev/null 2>&1'.format(server['hostname']), shell=True)
        call('paste -d "," ./{0}.dstat.dat ./{0}.iostat.dat > ./{0}.dat; rm -f ./{0}.dstat.dat ./{0}.iostat.dat'.format(server['hostname']), shell=True)
        COMMAND=("rm -f plot.dat")
        subprocess_cmd("root", server['hostname'], COMMAND)

    # Format data files
    for server in conf['servers']:
        tmp = open("tmpfile", "w")
        call(['sed', '1,7d', '{0}.dat'.format(server['hostname'])], stdout=tmp)
        call(['mv', 'tmpfile', '{0}.dat'.format(server['hostname'])])
    
    call(['rm', '-f', 'plot.gnu'])
    # Create GNU Plot file
    print "# Generating gnuplot configuration file"
    GNU_FILE=('set terminal png size 6144,3200 enhanced font "Helvetica,20"\n'
     'set output "output.png"\n'
     'set datafile separator ","\n'
     'set key outside left\n'
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
     'set multiplot layout 13,6 rowsfirst\n')
    
    
    for server in conf['servers']:
        GNU_FILE+=('# Network\n'
        'set label 1 "Network {0}" at graph 0.2,1.1 font ",8"\n'
        'set format y "%.0s%cB"\n'
        'plot "{0}.dat" u 2 w lp ls 1 t "Recv", "{0}.dat" u 3 w lp ls 2 t "Send"\n'
        '# IO\n'
        'set label 1 "IO {0}" at graph 0.2,1.1 font ",8"\n'
        'set format y "%.0s%cB"\n'
        'plot "{0}.dat" u 4 w lp ls 1 t "Read sdc", "{0}.dat" u 5 w lp ls 2 t "Write sdc", "{0}.dat" u 6 w lp ls 3 t "Read sdd", "{0}.dat" u 7 w lp ls 4 t "Write sdd"\n'
        '# CPU\n'
        'set label 1 "CPU {0}" at graph 0.2,1.1 font ",8"\n'
        'unset format\n'
        'plot "{0}.dat" u ($8+$9+$10+$11) w filledcurves x1 t "usr", \\\n'
             '"{0}.dat" u ($9+$10+$11) w filledcurves x1 t "idl", \\\n'
             '"{0}.dat" u ($9+$11) w filledcurves x1 t "sys", \\\n'
             '"{0}.dat" u ($11) w filledcurves x1 t "wait"\n'
        '# Memory\n'
        'set label 1 "Memory {0}" at graph 0.2,1.1 font ",8"\n'
        'set format y "%.0s%cB"\n'
        'plot "{0}.dat" u ($14+$15+$16+$17) w filledcurves x1 t "used", \\\n'
             '"{0}.dat" u ($15+$16+$17) w filledcurves x1 t "buf", \\\n'
             '"{0}.dat" u ($16+$17) w filledcurves x1 t "cache", \\\n'
             '"{0}.dat" u ($17) w filledcurves x1 t "free"\n'
        '# System stats\n'
        'set label 1 "System stats {0}" at graph 0.2,1.1 font ",8"\n'
        'set format y "%.0s%c"\n'
        'plot "{0}.dat" u 19 w lp ls 1 t "Csw"\n'
        '# Await\n'
        'set label 1 "Await {0}" at graph 0.2,1.1 font ",8"\n'
        'unset format\n'
        'plot "{0}.dat" u 20 w lp ls 1 t "Await sdc",\\\n'
             '"{0}.dat" u 21 w lp ls 21 t "Await sdd"\n').format(server['hostname'])
    
    GNU_FILE+=('unset multiplot')

    with open("plot.gnu", "w") as gnufile:
        gnufile.write(GNU_FILE)
    
    print "# Dumping graphs in output.png"
    call(['gnuplot', '-p', 'plot.gnu'])

if __name__ == "__main__":
    main()
