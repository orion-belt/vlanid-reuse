#!/usr/bin/env python3
"""
 * Copyright 2016-2019 Eurecom and Mosaic5G Platforms Authors
 * Licensed to the Mosaic5G under one or more contributor license
 * agreements. See the NOTICE file distributed with this
 * work for additional information regarding copyright ownership.
 * The Mosaic5G licenses this file to You under the
 * Apache License, Version 2.0  (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *-------------------------------------------------------------------------------
"""
import atexit
import os, time, sys
import json, csv
import argparse
import logging
from termcolor import colored

logging.basicConfig(format='%(asctime)s] %(filename)s:%(lineno)d %(levelname)s '
                           '- %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

class create_topology(object):
        def __init__(self, create_topo_log_level=None, ToRsw = None, sw = None, vm = None, pm = None):
            self.logger = logging.getLogger("vnir")
            atexit.register(self.goodbye)  # register a message to print out when exit
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
            self.dir_config = '../ns-allinone-3.29/ns-3.29/'
            self.file_name = 'example.csv'

        def build(self):
            pass

        def initiate_tree_topology(self):
            print(colored('[*] ToRsw = '+str(self.number_of_ToRsw)+', sw = '+str(self.number_of_sw)+', vm = '+str(self.number_of_vm)+', pm = '+str(self.number_of_pm),'cyan'))
            print(colored('So here each PM can host '+str(int(int(self.number_of_vm)/int(self.number_of_pm)))+' VMs','yellow'))
            responce = input(colored('Do you want to visualize topology [y/n] ? ','green'))
            if responce == 'y':
                os.system("cd ../ns-allinone-3.29/ns-3.29/ && ./waf --run new_topo --vis")
            else:
                os.system("cd ../ns-allinone-3.29/ns-3.29/ && ./waf --run new_topo ")
            print('\n')
            message = " Topology simulated"
            self.logger.info(message)
            self.parse_vm_info()
            time.sleep(2)

        def initiate_fat_tree_topology(self):
            raise NotImplementedError()

        def parse_vm_info(self):
            with open(''.join([self.dir_config, self.file_name])) as data_file:
                csv_data = csv.reader(data_file, delimiter=',')
                # data_file.close()
                line_count = 0
                for row in csv_data:
                    if line_count == 0:
                        print(f'Detailed info \n {", ".join(row)} \t\t')
                        line_count += 1
                    else:
                        print(f'\t{row[0]}  \t{row[1]}   \t{row[2]}  \t\t{row[3]}    \t{row[4]} \t{row[5]}  \t{row[6]}  \t\t{row[7]}  \t\t\t{row[8]}')
                        line_count += 1
                self.total_number_of_vm = (line_count-1) * int(row[2])
                # print(f'Processed {line_count} lines.')
                time.sleep(1)
                message = " vm_info parsed"
                self.logger.info(message)

        def get_tenant_request(self):
            sum = 0
            self.vm_array.clear()
            print(colored('[#] Ready to serve tenants. Press CTRL + C to exit anytime.','cyan'))
            number = input(colored("Enter the number of VN : ",'green'))
            print(colored('Enter number of VM required in each VN : ','green'))
            for i in range(int(number)):
                n = input("VN "+str(i+1)+" : ")
                sum = sum + int(n)
                self.vm_array.append(int(n))
            print('Tenant requested : ', self.vm_array)
            if sum > self.total_number_of_vm:
                print(colored("Excceds the total capacity !! Try Again !!!",'red'))
                self.get_tenant_request()
            time.sleep(1)

        def greedy_vm_selection(self):
            message = " Performing greedy search for locating vm"
            self.logger.info(message)
            # self.vm_array = [15, 22, 10, 25]
            total_required_vm = sum(self.vm_array)
            # time.sleep(2)
            ## Do algorithms here
            with open(''.join([self.dir_config, self.file_name])) as data_file:
                csv_data = csv.reader(data_file, delimiter=',')
                # data_file.close()
                line_count = 0
                for row in csv_data:
                    if line_count == 0:
                        print(f'Detailed info \n {", ".join(row)} \t\t')
                        line_count += 1
                    else:
                        # print('now', total_required_vm, ' ',self.number_of_vm)
                        if total_required_vm > self.number_of_vm:
                            if self.number_of_vm > 4096:
                                print('vlan usage limited')
                            print(f'\t{row[0]}  \t{row[1]}   \t{row[2]}  \t\t{row[3]}    \t{row[4]} \t{row[5]}  \t{self.number_of_vm}  \t\t{str(self.vlan_id_start+1)}-{str(self.vlan_id_start + self.number_of_vm)}  \t\t\t{self.number_of_vm-self.number_of_vm}')
                            total_required_vm = total_required_vm - self.number_of_vm
                            self.vlan_id_start = self.vlan_id_start + self.number_of_vm
                        elif total_required_vm < self.number_of_vm:
                            if total_required_vm > 4096:
                                print('vlan usage limited')
                            if total_required_vm == 0:
                                print(f'\t{row[0]}  \t{row[1]}   \t{row[2]}  \t\t{row[3]}    \t{row[4]} \t{row[5]}  \t{total_required_vm}  \t\t{str(self.vlan_id_start+1)}-{str(self.vlan_id_start + total_required_vm +1)}  \t\t\t{self.number_of_vm-total_required_vm}')
                            else:
                                print(f'\t{row[0]}  \t{row[1]}   \t{row[2]}  \t\t{row[3]}    \t{row[4]} \t{row[5]}  \t{total_required_vm}  \t\t{str(self.vlan_id_start+1)}-{str(self.vlan_id_start + total_required_vm)}  \t\t\t{self.number_of_vm-total_required_vm}')
                            total_required_vm = 0
                            self.vlan_id_start = -1

                        else:
                            pass
                            #print(f'\t{row[0]}  \t{row[1]}   \t{row[2]}  \t\t{row[3]}    \t{row[4]} \t{row[5]}  \t{row[6]}  \t\t{row[7]}  \t\t\t{row[8]}')
                        line_count += 1
                self.total_number_of_vm = (line_count-1) * int(row[2])
            ##
            self.get_tenant_request()

        def short_path_vm_selection(self):
            message = " Performing short_path search for locating vm"
            self.logger.info(message)

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

        parser.add_argument('--sw', metavar='[number]', action='store', type=str,
                            required=False, default='4',
                            help='set the switch number. default = 4')

        parser.add_argument('--pm', metavar='[number]', action='store', type=str,
                            required=False, default='5',
                            help='set the PM number per switch. default = 5')

        parser.add_argument('--vm', metavar='[number]', action='store', type=str,
                            required=False, default='20',
                            help='set the VM number per PM. default = 20')



        args = parser.parse_args()

        topo = create_topology(args.log, args.ToRsw, args.sw, args.vm, args.pm )
        topo.initiate_tree_topology()
        # topo.parse_vm_info()
        # topo.greedy_vm_selection()

        topo.get_tenant_request()
        topo.greedy_vm_selection()