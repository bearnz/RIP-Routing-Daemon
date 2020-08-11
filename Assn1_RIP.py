# COSC364-S1 2019 Assignment 1: RIP Routing
# Name: Josh Smith, Student ID: 32109650
# Name: Kate Olsen, Student ID: 79376467


# Things to be done next:
# add error checking for config file names

# Broken stuff:

# Imports
import sys
import time
import socket
import select
import numpy as np
import os

DEBUG = True


def end_program(message, socket_list=[]):
    """Closes the program following a provided error message."""
    for sock in socket_list:
        try:
            sock.close()
        except OSError:
            print('error: could not close socket')
    print(message)
    sys.exit(0)

def read_and_parse_config():
    """Handles opening, reading and closing the provided config file."""
    error_list = []
    # Get config file name from command parameter
    if len(sys.argv) != 2:
        print('Wrong number of inputs')
        sys.exit()
    config_file_name = sys.argv[1]
    

    # DEBUG
    if DEBUG:
        print("DEBUG - Config file name")
        print(config_file_name + "\n")

    # Open, read and close file
    file_exists = os.path.isfile(config_file_name)
    if file_exists:
        config = open(config_file_name, "r")
    else:
        print("Error - config file not found")
        sys.exit()
    config_raw = config.read()
    config.close()

    # DEBUG
    if DEBUG:
        print("DEBUG - Config raw")
        print(config_raw + "\n")

    # check what happens if there is an empty file
    config_lines = config_raw.split("\n")

    id_line = False
    input_line = False
    output_line = False
    timer_line = False

    # check that only one line of each appears
    for line in config_lines:
        if line.startswith('router-id'):
            id_line = line[10:]
        if line.startswith('input-ports'):
            input_line = line[12:]
        if line.startswith('outputs'):
            output_line = line[8:]
        if line.startswith('timer'):
            timer_line = line[6:].lstrip().rstrip()
        if line.startswith('router-id') and len(line) <= 9:
            error_list.append('Router-id error: no ids detected in config')
        if line.startswith('input-ports') and len(line) <= 11:
            error_list.append('Input-ports error: no ports detected in config')
        if line.startswith('outputs') and len(line) <= 7:
            error_list.append('Output ports error: no ports detected in config')
        if line.startswith('timer') and len(line) <= 5:
            error_list.append('Timer error: no timer value detected in config')
        

    if DEBUG: print('config lines', id_line, input_line, output_line, timer_line)

    if len(error_list) > 0:
        end_program('\n'.join(error_list))

    return [id_line, input_line, output_line, timer_line]


def create_sockets(port_list):
    """Creates as many sockets as there are ports in the config file"""
    socket_list = []
    for port in port_list:
        if DEBUG:
            print('creating socket')
            print('port: ', port)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except OSError:
            end_program("Socket creation failed.")
        try:
            # empty string to allow other computers to reach the server
            s.bind(('127.0.0.1', port))
        except OSError:
            socket_list.append(s)
            end_program("Binding of socket to port failed", socket_list)
        socket_list.append(s)
    return socket_list


def get_timer_value(timer_line):
    """Gets the update interval from the config file and checks validity"""
    error_list = []
    if timer_line == False:
        error_list.append('Timer value is missing from config file')
        return timer_line, error_list
    elif timer_line is None:
        error_list.append('Timer value is Nonetype')
        return timer_line, error_list    
    elif timer_line.isdigit() == False:
        error_list.append('Timer value ' + timer_line + ' is not an integer')
        return timer_line, error_list
    else:
        timer_value = int(timer_line)
        if timer_value < 0 or timer_value > 30:  # if its bigger than 30 then its slower than the RIP specification and that is not wanted
            error_list.append('Timer value needs to be between 0 and 30')

    # DEBUG
    if DEBUG:
        print("DEBUG - Timer Value")
        print(timer_value)

    return timer_value, error_list


def get_input_ports(inputs):
    """Gets the input ports from the config file and checks validity"""
    # Verify input-ports line is in correct format
    input_ports = []
    error_list = []
    # Verify line prefix
    if inputs == False:
        error_list.append("input-ports line is missing from config file.\n")
        return inputs, error_list
    # Verify value exists
    elif inputs == "":
        error_list.append("input value(s) are missing.\n")
        return inputs, error_list
    else:
        for input_port_str in inputs.split(", "):
            # Verify input port is a positive integer
            if input_port_str.isdigit() == False:
                error_list.append("Input port " + input_port_str + " is not an integer.\n")
                return inputs, error_list
            # Verify input port is in range 1024 - 64000.
            elif int(input_port_str) not in range(1024, 64001):
                error_list.append("Input port " + input_port_str + " is not in range 1024 - 64000.\n")
                return inputs, error_list
            # Append input port value to list
            else:
                input_ports.append(int(input_port_str))

    # DEBUG
    if DEBUG:
        print("DEBUG - Input Ports")
        print(str(input_ports) + "\n")

    return input_ports, error_list


def get_output_ports(outputs_line):
    """Gets the output ports from the config file and checks validity"""
    # Verify outputs line is in correct format
    outputs = []
    error_list = []
    # Verify line prefix
    if outputs_line == False:
        error_list.append("outputs line is missing from config file.\n")
    # Verify value exists
    elif outputs_line == "":
        error_list.append("outputs value(s) are missing.\n")
    else:
        for output_str in outputs_line.split(", "):
            single_output = output_str.split("-")
            # Check output consists of 3 parts
            if len(single_output) != 3:
                error_list.append("Output triple " + output_str + " has more or less than 3 values.\n")
                return outputs_line, error_list
                # continue
            # Check output port is a positive integer
            elif single_output[0].isdigit() == False:
                error_list.append(
                    "Output port " + single_output[0] + " from triple " + output_str + " is not a positive integer.\n")
                return outputs_line, error_list
            # Check port in range
            elif int(single_output[0]) not in range(1024, 64001):
                error_list.append(
                    "Output port " + single_output[0] + " from triple " + output_str + " not in range 1024 - 64000.\n")
                return outputs_line, error_list
            # Check metric is a positive integer
            elif single_output[1].isdigit() == False:
                error_list.append("Output triple metric value " + single_output[
                    1] + " from triple " + output_str + " is not a positive integer.\n")
                return outputs_line, error_list
            # Check router-id is a positive integer
            elif (single_output[2].isdigit() and int(single_output[2]) >= 0) == False:
                error_list.append("Output router id " + single_output[
                    2] + " from triple " + output_str + " is not a positive integer.\n")
                return outputs_line, error_list
            else:
                outputs.append(single_output)

    # DEBUG
    if DEBUG:
        print("DEBUG - Outputs")
        for i in outputs:
            print(str(i))

    return outputs, error_list

def get_router_id(router_id):
    """Gets the router id from the config file"""
    error_list = []
    if router_id == False:
        error_list.append('Router-id line is missing from config file')
        return router_id, error_list
    elif router_id.isdigit() == False:
        error_list.append('Router-id value ' + router_id + ' is not an integer')
        return router_id, error_list
    else:
        id_number = int(router_id)
        if id_number < 1 or id_number > 64000:
            error_list.append('router-id is not in range 1-64000')
            return router_id, error_list

    # DEBUG
    if DEBUG:
        print("DEBUG - Router ID")
        print(str(router_id) + "\n")

    return id_number, error_list


def get_next_timeout(routing_table, update_time):
    """Gets the next timeout time for the alive routers in the routing table"""
    # possible change this to a sorted list that is mainted instead of creating a new list each time
    next_key = False
    wait_time = update_time
    keys = routing_table.keys()
    for key in keys:
        if routing_table[key]["timeout"] != False and routing_table[key][
            "timeout"] < wait_time:  # this syntax should work
            next_key = key
            wait_time = routing_table[key]["timeout"]
        if routing_table[key]["garbage_collection"] < wait_time:
            next_key = key
            wait_time = routing_table[key]["garbage_collection"]
    return wait_time, next_key


def create_update(routing_table, port, my_id):
    """Creates rip updates and implements split horizon with poison reverse"""
    command = 0x02  #2 = response
    version = 0x02
    my_id = (my_id).to_bytes(2, byteorder='big')
    address_family_identifier = (2).to_bytes(2, byteorder='big')  # AF_INET
    keys = routing_table.keys()
    header = bytearray([command, version]) + my_id
    rip_entries = []

    for key in keys:
        ipv4_address = (int(key)).to_bytes(4, byteorder='big')
        # split horizon
        if port == routing_table[key]["my_out"]:
            metric = (16).to_bytes(4, byteorder='big')
        else:
            metric = (routing_table[key]["metric"]).to_bytes(4, byteorder='big')

        rip_entry = address_family_identifier + bytearray(2) + ipv4_address + bytearray(8) + metric
        rip_entries.append(rip_entry)

    message = header
    for rip_entry in rip_entries:
        message += rip_entry
    return message


def print_update_message(data):
    """Prints each rip update message as they arrive"""
    message_length = len(data)
    print('command: ', data[0])
    print('version: ', data[1])
    print('my router id: ', int.from_bytes(data[2:4], byteorder='big'))
    for i in range((message_length - 4) // 20):
        print('rip entry: ', i)
        print('address family identifier: ', int.from_bytes(data[i * 20 + 4: i * 20 + 4 + 2], byteorder='big'))
        print('should be zero: ', int.from_bytes(data[i * 20 + 4 + 2: i * 20 + 4 + 4], byteorder='big'))
        print('ipv4 address: ', int.from_bytes(data[i * 20 + 4 + 4: i * 20 + 4 + 8], byteorder='big'))
        print('should be zero: ', int.from_bytes(data[i * 20 + 4 + 8: i * 20 + 4 + 12], byteorder='big'))
        print('should be zero: ', int.from_bytes(data[i * 20 + 4 + 12: i * 20 + 4 + 16], byteorder='big'))
        print('metric: ', int.from_bytes(data[i * 20 + 4 + 16: i * 20 + 4 + 20], byteorder='big'))
    return


def space8join(thelist):
    """Adds spacing to ensure correct formatting of the routing table values"""
    outstring = ''
    for thing in thelist:
        if type(thing) is int and thing <= 0:
            thing = ''
        outstring += '%8s' % (thing)
    return outstring


def print_routing_table(routing_table, my_router_id):
    """Prints the whole routing table for this router"""
    router_ids = list(routing_table.keys())
    if len(router_ids) > 0:
        router_ids.sort()
    metrics = []
    timeouts = []
    garbage_collections = []
    update_flags = []
    next_hops = []
    for router_id in router_ids:
        metrics.append(routing_table[router_id]['metric'])
        timeouts.append(int(routing_table[router_id]['timeout'] - time.time()))
        garbage_collections.append(int(routing_table[router_id]['garbage_collection'] - time.time()))
        update_flags.append(routing_table[router_id]['update_flag'])
        next_hops.append(routing_table[router_id]['next_hop'])

    print('--------------------------------------------------------------------------------')
    print('This router is router ', my_router_id)
    print('Router ID:                   ', space8join(router_ids))
    print('Metric:                      ', space8join(metrics))
    print('Dead route countdown:        ', space8join(timeouts))
    print('Garbage collection countdown:', space8join(garbage_collections))
    print('Update Flag:                 ', space8join(update_flags))
    print('Next hop:                    ', space8join(next_hops))
    print('--------------------------------------------------------------------------------')
    
def check_incoming_packet(data, address, neighbour_info):
    """Checks incoming data packet for correct header fields"""
    # need to check that router id matches the port it came in on
    their_port = address[1]
    total_correctness = False
    header_correctness = False
    metric_correctness = True
    length_correctness = True
    address_correctness = True
    zero_correctness = True
    afi_correctness = True
    if data[0] == 2 and data[1] == 2: #correct packet type and version
        for neighbour in neighbour_info:
            if int(neighbour[2]) == int.from_bytes(data[2:4], byteorder='big') :
                if int(neighbour[0]) == their_port:
                    header_correctness = True
                else:
                    print("Error: Invalid receiving address in packet header")
    else:
        print("Error: Invalid packet command type (should be response) or invalid rip version (should be 2)")
    
    if len(data) > 4:
        for i in range((len(data)-4)//20):
            #Checks if the metrics are integers
            try:
                int.from_bytes(data[i * 20 + 4 + 16: i * 20 + 4 + 20], byteorder='big')
            except TypeError:
                metric_correctness = False
            #Checks if the metric is nonzero and less than the max allowable metric
            if int.from_bytes(data[i * 20 + 4 + 16: i * 20 + 4 + 20], byteorder='big') <= 0 and \
                    int.from_bytes(data[i * 20 + 4 + 16: i * 20 + 4 + 20], byteorder='big') > 16:
                metric_correctness = False
            #Checks if the must be zero bytes are zero
            if int.from_bytes(data[i * 20 + 4 + 8: i * 20 + 4 + 16], byteorder='big') != 0 or \
                    int.from_bytes(data[i * 20 + 4 + 2: i * 20 + 4 + 4], byteorder='big') != 0:
                zero_correctness = False
            #check the address family identifier
            try:
                if int.from_bytes(data[i * 20 + 4: i * 20 + 4 + 2], byteorder='big') != 2:
                    afi_correctness = False
            except TypeError:
                afi_correctness = False
            #Checks if the router id in the rip packet is an integer
            try:
                int.from_bytes(data[i * 20 + 4 + 4: i * 20 + 4 + 8], byteorder='big')
            except TypeError:
                address_correctness = False
            #Checks if the router id is in the expected range
            if int.from_bytes(data[i * 20 + 4 + 4: i * 20 + 4 + 8], byteorder='big') < 1 or \
                        int.from_bytes(data[i * 20 + 4 + 4: i * 20 + 4 + 8], byteorder='big') > 64000:
                address_correctness = False
        #Checks the length of the rip entry packet is the correct size
        if (len(data) - 4) % 20 != 0:
            length_correctness = False
    if header_correctness and length_correctness and metric_correctness and zero_correctness and address_correctness and afi_correctness:
        total_correctness = True
    return total_correctness
    

def process_data_from_socket(my_id, routing_table, data, their_address, my_address, dead_value, purge_value, neighbour_info):
    """Update the routing information from the incoming update message."""
    if DEBUG: print('updating data')
    update_length = len(data)
    current_time = time.time()
    in_table = list(routing_table.keys()) 
    timeout_value = dead_value + current_time
    garbage_value = purge_value + current_time
    incoming_port = my_address[1]
    distance = None
    neighbour_id = int.from_bytes(data[2:4], byteorder='big')

    

    if DEBUG: print('neighbour_id: ', neighbour_id)
    # deal with the directly connected node
    #For adding direct neighbours into the routing table
    for neighbour in neighbour_info:
        if int(neighbour[2]) == neighbour_id:
            metric = int(neighbour[1])
            their_in = int(neighbour[0])
            if neighbour_id not in in_table or metric < routing_table[neighbour_id]['metric']:
                if DEBUG: print('updating connected router', neighbour_id, 'to metric', metric)
                # check that more than one router with the same id does not exist
                if neighbour_id == my_id:
                    print('This router is a duplicate. Ending program.')
                    sys.exit()
                routing_table.update({neighbour_id : {"metric": metric, "my_out": incoming_port, "their_in": their_in,
                                       "update_flag": False, "timeout": timeout_value, "next_hop": neighbour_id,
                                       "garbage_collection": garbage_value}})
                in_table.append(neighbour_id)
            else:
                routing_table[neighbour_id].update({"timeout" :timeout_value})
                routing_table[neighbour_id].update({"garbage_collection" : garbage_value})
            distance = metric

    # for each node that the neighbour router has in its routing table
    #for adding routes into the routing table
    for i in range((update_length-4)//20):
        rip_node = int.from_bytes(data[i * 20 + 4 + 4: i * 20 + 4 + 8], byteorder='big')
        neighbour_metric = int.from_bytes(data[i * 20 + 4 + 16: i * 20 + 4 + 20], byteorder='big')
        metric = distance + neighbour_metric
        if rip_node != my_id and rip_node != neighbour_id:
            #if the connected router in the rip update is not known to this router, then add it to the routing 
            #table with the metric rom the origin of the origin of the rip update + the distance to that origin
            if rip_node not in in_table:
                if DEBUG: print('adding route', rip_node)
                if metric < 16: # don't add invalid routes
                    their_in = routing_table[neighbour_id]["their_in"]
                    my_out = routing_table[neighbour_id]["my_out"]
                    routing_table.update({ rip_node : {"metric": metric, "my_out": my_out, "their_in": their_in, 
                                "update_flag": False, "timeout": timeout_value, "garbage_collection": garbage_value, "next_hop": neighbour_id}})

            #if the connected router in the update is known and it's distance in the update is smaller than 
            #the distance in the current routing table, update the table with the smaller distance and route
            elif metric < routing_table[rip_node]["metric"]:
                if DEBUG: print('what is this: ', distance, neighbour_metric,  routing_table[rip_node]["metric"], 'for id', rip_node)
                their_in = routing_table[neighbour_id]["their_in"]
                my_out = routing_table[neighbour_id]["my_out"]
                routing_table.update({ rip_node : {"metric": metric, "my_out": my_out, "their_in": their_in, "update_flag": False, 
                        "timeout": timeout_value, "garbage_collection": garbage_value, "next_hop": neighbour_id}})

            # update the timervalues if the route is still a valid route in the routing table
            elif routing_table[rip_node]["their_in"] == routing_table[neighbour_id]["their_in"] and routing_table[rip_node]["metric"] != 16:
                if metric > 16:
                    metric = 16
                if DEBUG: print('just updating timers for id', rip_node)
                if metric < 16:
                    routing_table[rip_node].update({"timeout" :timeout_value})
                    routing_table[rip_node].update({"garbage_collection" : garbage_value})
                else:
                    routing_table[rip_node].update({"timeout" :False})
                    routing_table[rip_node].update({"garbage_collection" : (purge_value - dead_value) + current_time})
                routing_table[rip_node].update({"metric":metric})
                    
    if DEBUG: print('ending update of routing table')
    return routing_table


def clean_up_routing_table(routing_table):
    """If one dead route timeout goes off, check through all the other timeouts."""
    other_routers = list(routing_table.keys()) 
    for router in other_routers:
        if routing_table[router]["timeout"] != False and routing_table[router]["timeout"] < time.time():
            routing_table[router]["timeout"] = False
            routing_table[router]["metric"] = 16
    return routing_table


def main_loop(socket_list, router_id, timer_value, outputs):
    wait_time = False
    next_item = False
    next_allowed_update = time.time() + np.random.uniform(1 / (30 / timer_value), 5 / (
            30 / timer_value))  # change this value to a random number
    next_update = time.time() + timer_value  # change this value to a random number
    my_id = router_id
    neighbour_info = outputs
    dead_route_timer_value = timer_value * 6
    purge_route_timer_value = timer_value * 10

    routing_table = {}
    print_routing_table(routing_table, my_id)

    while True:
        try:
            # get next thing to do and the time that it needs to be to happen
            wait_time, next_item_key = get_next_timeout(routing_table, next_update)

            # while it is not time for the next thing to happen
            while wait_time > time.time():

                # listen to the ports
                try:
                    readable, writeable, errors = select.select(socket_list, [], [], wait_time - time.time())
                except OSError:
                    end_program('Checking ports for inputs failed', socket_list)
                # if there is any readable ports read from them
                for ready_socket in readable:
                    try:
                        data, their_address = ready_socket.recvfrom(504)  # 20 * 25 + 4 bytes
                        if DEBUG: print_update_message(data)
                        my_address = ready_socket.getsockname()
                        if DEBUG: print('\nI recieved data', data, 'address ', my_address)
                        correct = check_incoming_packet(data, their_address, neighbour_info)
                        if correct:
                            routing_table = process_data_from_socket(my_id, routing_table, data, their_address, my_address,
                                                                 dead_route_timer_value, purge_route_timer_value,
                                                                 neighbour_info)
                    except KeyError:
                        print("Failed to read socket")
                    print_routing_table(routing_table, router_id)
                    wait_time, next_item_key = get_next_timeout(routing_table, next_update)

            # now there is something to do
            # if the next item was an update
            if next_item_key == False:
                next_update = time.time() + np.random.uniform(0.8 * timer_value, 1.2 * timer_value)
                next_allowed_update = time.time() + np.random.uniform(1 / (30 / timer_value), 5 / (
                        30 / timer_value))  
                for i, out_socket in enumerate(socket_list):
                    out_port = out_socket.getsockname()[1]
                    send_to_port = int(outputs[i][0])
                    if DEBUG: print('\nsending to port ', send_to_port)
                    update_message = create_update(routing_table, out_port, my_id)
                    out_socket.sendto(update_message, ('127.0.0.1', send_to_port))
                    if DEBUG:
                        print('update message')
                        print_update_message(update_message)
                        print('end of update message\n')

            # if the next item was associated with a route failing
            elif routing_table[next_item_key]["timeout"] != False:
                routing_table = clean_up_routing_table(routing_table)
                if next_allowed_update < time.time():
                    next_update = time.time()
                else:
                    next_update = next_allowed_update
                print_routing_table(routing_table, my_id)
                if DEBUG: print('Route failed, setting up garbage collection')

            # if the next item is garabe collection
            else:
                del routing_table[next_item_key]
                print_routing_table(routing_table, my_id)
                if DEBUG: print('Garbage collection ativated')
        except KeyboardInterrupt:
            end_program('closed through keyboard', socket_list)


def check_for_errors(error_list2, error_list3, error_list4, error_list5):
    excep_msg = ""
    if len(error_list2) > 0:
        excep_msg += "__Router ID Errors__\n" + '\n'.join(error_list2) + "\n"
    if len(error_list3) > 0:
        excep_msg += "__Input Ports Errors__\n" + '\n'.join(error_list3) + "\n"
    if len(error_list4) > 0:
        excep_msg += "__Outputs Errors__\n" + '\n'.join(error_list4) + "\n"
    if len(error_list5) > 0:
        excep_msg += "__Timer Errors__\n" + '\n'.join(error_list5) + "\n"
    if len(excep_msg) > 0:
        print(excep_msg)
        sys.exit()


def main():
    # Read and parse config
    config_list = read_and_parse_config()
    router_id, error_list2 = get_router_id(config_list[0])    
    inputs, error_list3 = get_input_ports(config_list[1])    
    outputs, error_list4 = get_output_ports(config_list[2])    
    timer_value, error_list5 = get_timer_value(config_list[3])
    check_for_errors(error_list2, error_list3, error_list4, error_list5)

    sockets = create_sockets(inputs)

    main_loop(sockets, router_id, timer_value, outputs)

    return


if __name__ == '__main__':
    main()

