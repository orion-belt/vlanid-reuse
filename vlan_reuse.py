#!/usr/bin/env python3

import atexit
import os, time, sys
import json, csv
import argparse
import logging
from termcolor import colored
import subprocess

logging.basicConfig(format='%(asctime)s] %(filename)s:%(lineno)d %(levelname)s '
                           '- %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

class algo_vlan_reuse(object):
    def __init__(self, create_topo_log_level=None, ToRsw=None, sw=None, vm=None, pm=None):
        self.logger = logging.getLogger("vnir")
        #   atexit.register(self.goodbye)  # register a message to print out when exit
        if create_topo_log_level:
            if create_topo_log_level == 'debug':
                self.logger.setLevel(logging.DEBUG)
            elif create_topo_log_level == 'info':
                self.logger.setLevel(logging.INFO)
            elif create_topo_log_level == 'warn':
                self.logger.setLevel(logging.WARNING)
            elif create_topo_log_level == 'error':
                self.logger.setLevel(logging.ERROR)
            elif create_topo_log_level == 'critic':
                self.logger.setLevel(logging.CRITICAL)

        self.number_of_ToRsw = int(ToRsw)
        self.number_of_sw = int(sw)
        self.number_of_vm = int(vm)
        self.number_of_pm = int(pm)
        self.total_number_of_vm = None
        self.VM_subnet = None
        self.domain = None
        self.capacity = None
        self.corresponding_PM = None
        self.ip_start = None
        self.ip_end = None
        self.allocated_vm = None
        self.vlan_id_start = 0
        self.allocated_VLANID = None
        self.available_vm_per_subnet = None
        self.total_available_vm = None
        self.tenant_req = None
        self.vm_array = list()

    def build(self):
        pass

    def initiate_tree_topology(self):
        print(colored('[*] ToRsw = ' + str(self.number_of_ToRsw) + ', edegesw = ' + str(self.number_of_sw) + ', pm = ' + str(
            self.number_of_pm * self.number_of_sw) + ', vm = ' + str(self.number_of_vm * self.number_of_sw), 'cyan'))
        print(colored('So here each PM can host ' + str(int(int(self.number_of_vm) / int(self.number_of_pm))) + ' VMs',
                      'yellow'))
        # sudo python -E SDN_PGS.py  -t topology.json -i host.csv -s 6
        # subprocess.call_in_new_window('ifconfig', shell=True)
        subprocess.CREATE_NEW_CONSOLE('ifconfig', shell=True)
        #os.system("gnome-terminal -e 'ifconfig && sleep 10'")

    def goodbye(self):
        print(colored('[*] You are now leaving framework .....', 'red'))
        sys.exit(0)


if __name__ == '__main__':
        parser = argparse.ArgumentParser(
            description='Process commandline arguments and override configurations')
        parser.add_argument('--log', metavar='[level]', action='store', type=str,
                            required=False, default='debug',
                            help='set the log level: debug, info (default), warning, error, critical. default = info')

        parser.add_argument('--ToRsw', metavar='[number]', action='store', type=str,
                            required=False, default='2',
                            help='set the ToR switch number. default = 2')

        parser.add_argument('--edege_sw', metavar='[number]', action='store', type=str,
                            required=False, default='4',
                            help='set the edege switch number. default = 4')

        parser.add_argument('--pm', metavar='[number]', action='store', type=str,
                            required=False, default='1',
                            help='set the PM number per switch. default = 1')

        parser.add_argument('--vm', metavar='[number]', action='store', type=str,
                            required=False, default='10',
                            help='set the VM number per PM. default = 10')

        args = parser.parse_args()

        algo = algo_vlan_reuse(args.log, args.ToRsw, args.edege_sw, args.vm, args.pm )
        algo.initiate_tree_topology()
        # topo.parse_vm_info()
        # topo.greedy_vm_selection()

        # algo.get_tenant_request()
        # algo.greedy_vm_selection()
