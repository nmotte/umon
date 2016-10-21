BIG_SERVERS="ns6737901.ip-164-132-166.eu ns6737902.ip-164-132-166.eu ns6737903.ip-164-132-166.eu ns6737904.ip-164-132-166.eu ns6737905.ip-164-132-166.eu ns6737906.ip-164-132-166.eu ns6737908.ip-164-132-166.eu ns6737909.ip-164-132-166.eu"
SMALL_SERVERS="ns6736510.ip-164-132-166.eu ns6736511.ip-164-132-166.eu ns6736512.ip-164-132-166.eu ns6736513.ip-164-132-166.eu ns6736514.ip-164-132-166.eu"
ALL_SERVERS="ns6737901.ip-164-132-166.eu ns6737902.ip-164-132-166.eu ns6737903.ip-164-132-166.eu ns6737904.ip-164-132-166.eu ns6737905.ip-164-132-166.eu ns6737906.ip-164-132-166.eu ns6737908.ip-164-132-166.eu ns6737909.ip-164-132-166.eu ns6736510.ip-164-132-166.eu ns6736511.ip-164-132-166.eu ns6736512.ip-164-132-166.eu ns6736513.ip-164-132-166.eu ns6736514.ip-164-132-166.eu"

# Start dstat
for SERVER in $BIG_SERVERS
do
echo "# Starting dstat on ${SERVER}"
ssh -o "StrictHostKeyChecking no" root@$SERVER << EOF > /dev/null 2>&1&
nohup dstat --noheaders -t -n -N eth1 -d -D sdd,sdc -c -m -y --output plot.dat 5 > /dev/null 2>&1&
ps aux | grep dstat | grep plot.dat | awk '{print \$2}' > dstat.pid
EOF
done
for SERVER in $SMALL_SERVERS
do
echo "# Starting dstat on ${SERVER}"
ssh -o "StrictHostKeyChecking no" root@$SERVER << EOF > /dev/null 2>&1&
nohup dstat --noheaders -t -n -N eth1 -d -D sda,sdb -c -m -y --output plot.dat 5 > /dev/null 2>&1&
ps aux | grep dstat | grep plot.dat | awk '{print \$2}' > dstat.pid
EOF
done


# Wait for test
echo "# Monitoring for $1 seconds..."
sleep $1

# Stop dstat
for SERVER in $ALL_SERVERS
do
echo "# Stopping dstat on ${SERVER}"
ssh -o "StrictHostKeyChecking no" root@$SERVER << EOF > /dev/null 2>&1
cat dstat.pid | xargs kill
rm -f dstat.pid
EOF
done

# Gather stats
for SERVER in $ALL_SERVERS
do
echo "# Retrieving stats from ${SERVER}"
scp -o "StrictHostKeyChecking no" root@$SERVER:./plot.dat ./${SERVER}.dat > /dev/null 2>&1
ssh -o "StrictHostKeyChecking no" root@$SERVER << EOF > /dev/null 2>&1
rm -f plot.dat
EOF
done

# Format data files
for SERVER in $ALL_SERVERS
do
sed '1,6d' ${SERVER}.dat > tmpfile; mv tmpfile ${SERVER}.dat
done

rm -f plot.gnu
# Create GNU Plot file
echo "# Generating gnuplot configuration file"
cat << EOF >> plot.gnu
set terminal png size 5120,3200 enhanced font "Helvetica,20"
set output 'output.png'
set datafile separator ","
set key outside left
set style line 80 lt 0 lc rgb "#808080"
set border 3 back ls 80 
set style line 81 lt 0 lc rgb "#808080" lw 0.5
set grid back ls 81
set style line 1 lt 1 lc rgb "#A00000" lw 2 pt 7 ps 1
set style line 2 lt 1 lc rgb "#00A000" lw 2 pt 11 ps 1
set style line 3 lt 1 lc rgb "#5060D0" lw 2 pt 9 ps 1
set style line 4 lt 1 lc rgb "#0000A0" lw 2 pt 8 ps 1
set style line 5 lt 1 lc rgb "#D0D000" lw 2 pt 13 ps 1
set style line 6 lt 1 lc rgb "#00D0D0" lw 2 pt 12 ps 1
set style line 7 lt 1 lc rgb "#B200B2" lw 2 pt 5 ps 1
set multiplot layout 13,5 rowsfirst
EOF

for SERVER in $ALL_SERVERS
do
cat << EOF >> plot.gnu
# Network
set label 1 'Network ${SERVER}' at graph 0.2,1.1 font ',8'
set format y '%.0s%cB'
plot "${SERVER}.dat" u 2 w lp ls 1 t "Recv", "${SERVER}.dat" u 3 w lp ls 2 t "Send"
# IO
set label 1 'IO ${SERVER}' at graph 0.2,1.1 font ',8'
set format y '%.0s%cB'
plot "${SERVER}.dat" u 4 w lp ls 1 t "Read sdc", "${SERVER}.dat" u 5 w lp ls 2 t "Write sdc", "${SERVER}.dat" u 6 w lp ls 3 t "Read sdd", "${SERVER}.dat" u 7 w lp ls 4 t "Write sdd"
# CPU
set label 1 'CPU ${SERVER}' at graph 0.2,1.1 font ',8'
unset format
plot "${SERVER}.dat" u (\$8+\$9+\$10+\$11) w filledcurves x1 t "usr", \
     "${SERVER}.dat" u (\$9+\$10+\$11) w filledcurves x1 t "idl", \
     "${SERVER}.dat" u (\$9+\$11) w filledcurves x1 t "sys", \
     "${SERVER}.dat" u (\$11) w filledcurves x1 t "wait"
# Memory
set label 1 'Memory ${SERVER}' at graph 0.2,1.1 font ',8'
set format y '%.0s%cB'
plot "${SERVER}.dat" u (\$14+\$15+\$16+\$17) w filledcurves x1 t "used", \
     "${SERVER}.dat" u (\$15+\$16+\$17) w filledcurves x1 t "buf", \
     "${SERVER}.dat" u (\$16+\$17) w filledcurves x1 t "cache", \
     "${SERVER}.dat" u (\$17) w filledcurves x1 t "free"
# System stats
set label 1 'System stats ${SERVER}' at graph 0.2,1.1 font ',8'
unset format
plot "${SERVER}.dat" u 2 w lp ls 1 t "Csw"
EOF
done

cat << EOF >> plot.gnu
unset multiplot
EOF

echo "# Dumping graphs in output.png"
gnuplot -p plot.gnu &
