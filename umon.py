from optparse import OptionParser
import json, uuid, os
import subprocess, sys, time
from subprocess import call

def subprocess_cmd(user, host, command):
    ssh = subprocess.Popen("ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 {0}@{1} ".format(user, host) + command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    parser.add_option("-s", "--sampling", type='int', dest="sampling", default=5)
    (options, args) = parser.parse_args()

    uid = str(uuid.uuid4())
    print "Monitoring UID: {0}".format(uid)

    with open(".uid", "w") as tmp:
        tmp.write(uid)

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
        print("# Starting dstat and iostat on {0}").format(server['hostname'])
        COMMAND=('\'nohup dstat --noheaders -t -n -N {3} -d -D {1} -c -m -y --output dstat.dat {4} > /dev/null 2>&1&'
        'echo $! > dstat.{0}.pid;'
        'nohup iostat -d -x -m -p {1} {4} | awk "/{2}\ / {{print \$10; fflush(stdout)}}" | awk "NR%{5}!=0 {{printf \$0;printf \\",\\";fflush(stdout)}} NR%{5}==0 {{printf \$0;print \\"\\";fflush(stdout)}}" > iostat.dat&'
        'echo $! > iostat.{0}.pid;\'').format(uid, ','.join(server['device']), '\ |'.join(server['device']), ','.join(server['interface']), options.sampling, len(server['device']))
        subprocess_cmd("root", server['hostname'], COMMAND)
    
    # Wait for test
    print("# Monitoring for {0} seconds...").format(options.time)
    time.sleep(options.time)
    
    # Stop dstat
    for server in conf['servers']:
        print("# Stopping dstat and iostat on {0}").format(server['hostname'])
        COMMAND=('\'kill `cat dstat.{0}.pid`;kill `cat iostat.{0}.pid`;rm -f iostat.{0}.pid dstat.{0}.pid;\'').format(uid)
        subprocess_cmd("root", server['hostname'], COMMAND)

    # Gather stats
    for server in conf['servers']:
        print "# Retrieving and merging stats from {0}".format(server['hostname'])
        call('scp -o "StrictHostKeyChecking no" -o ConnectTimeout=2 root@{0}:./dstat.dat ./{0}.dstat.dat > /dev/null 2>&1'.format(server['hostname']), shell=True)
        with open("tmpfile", "w") as tmp:
            call(['sed', '1,7d', '{0}.dstat.dat'.format(server['hostname'])], stdout=tmp)
        call(['mv', 'tmpfile', '{0}.dstat.dat'.format(server['hostname'])])
        call('scp -o "StrictHostKeyChecking no" -o ConnectTimeout=2 root@{0}:./iostat.dat ./{0}.iostat.dat > /dev/null 2>&1'.format(server['hostname']), shell=True)
        call('paste -d "," ./{0}.dstat.dat ./{0}.iostat.dat > ./{0}.dat; rm -f ./{0}.dstat.dat ./{0}.iostat.dat'.format(server['hostname']), shell=True)
        COMMAND=("rm -f dstat.dat iostat.dat")
        subprocess_cmd("root", server['hostname'], COMMAND)

    call(['rm', '-f', 'umon.gnu'])
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
        GNU_FILE+=(
            # Network
            'set label 1 "Network {0}" at graph 0.2,1.1 font ",8"\n'
            'set format y "%.0s%cB"\n'
            'plot "{0}.dat" u 2 w lp ls 1 t "Recv", "{0}.dat" u 3 w lp ls 2 t "Send"\n'
            # IO
            'set label 1 "IO {0}" at graph 0.2,1.1 font ",8"\n'
            'set format y "%.0s%cB"\n'
        ).format(server['hostname'])

        GNU_FILE+='plot '
        line_style = 1
        field = 4 
        devices = []
        for device in server['device']:
            devices.append(('"{0}.dat" u {1} w lp ls {2} t "Read {3}"').format(server['hostname'], field, line_style, device))
            line_style+=1
            field+=1
            devices.append(('"{0}.dat" u {1} w lp ls {2} t "Write {3}"').format(server['hostname'], field, line_style, device))
            line_style+=1
            field+=1
        GNU_FILE+=','.join(devices)+'\n'

        # CPU
        GNU_FILE+=(
            'set label 1 "CPU {0}" at graph 0.2,1.1 font ",8"\n'
            'unset format\n'
            'plot "{0}.dat" u (${1}+${2}+${3}+${4}) w filledcurves x1 t "usr", \\\n'
                 '"{0}.dat" u (${2}+${3}+${4}) w filledcurves x1 t "idl", \\\n'
                 '"{0}.dat" u (${2}+${4}) w filledcurves x1 t "sys", \\\n'
                 '"{0}.dat" u (${4}) w filledcurves x1 t "wait"\n'
            # Memory
            'set label 1 "Memory {0}" at graph 0.2,1.1 font ",8"\n'
            'set format y "%.0s%cB"\n'
            'plot "{0}.dat" u (${5}+${6}+${7}+${8}) w filledcurves x1 t "used", \\\n'
                 '"{0}.dat" u (${6}+${7}+${8}) w filledcurves x1 t "buf", \\\n'
                 '"{0}.dat" u (${7}+${8}) w filledcurves x1 t "cache", \\\n'
                 '"{0}.dat" u (${8}) w filledcurves x1 t "free"\n'
            # System stats
            'set label 1 "System stats {0}" at graph 0.2,1.1 font ",8"\n'
            'set format y "%.0s%c"\n'
            'plot "{0}.dat" u {9} w lp ls 1 t "Csw"\n'
            # Await
            'set label 1 "Await {0}" at graph 0.2,1.1 font ",8"\n'
            'unset format\n'
        ).format(server['hostname'], field, field+1, field+2, field+3, field+6, field+7, field+8, field+9, field+11)

        GNU_FILE+='plot '
        line_style = 1
        field += 12
        devices = []
        for device in server['device']:
            devices.append(('"{0}.dat" u {1} w lp ls {2} t "Await {3}"').format(server['hostname'], field, line_style, device))
            line_style+=1
            field+=1
        GNU_FILE+=','.join(devices)+'\n'
    
    GNU_FILE+=('unset multiplot')

    with open("umon.gnu", "w") as gnufile:
        gnufile.write(GNU_FILE)
    
    print "# Dumping graphs in output.png"
    call(['gnuplot', '-p', 'umon.gnu'])

    os.remove('.uid')

if __name__ == "__main__":
    main()
