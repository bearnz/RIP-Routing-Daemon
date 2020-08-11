# COSC364-RIP-Routing-Daemon

This is a RIP routing daemon that was developed as a group project assignment for my final year of Computer Science at the University of Canterbury.
It is designed to be run from the Linux command line with a series of config files. Each command window will run 1 copy of the daemon with different config files.

Config files are in the format:

router-id <id_num>

input-ports <port_num1, port_num2, ..., <port_numx>

output-ports <port_num1-metric-inp_port1, ..., port_numx-metric-inp_portx>

timer <value>
  
