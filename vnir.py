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
import os, time, sys
import json, csv
import argparse
import logging
logging.basicConfig(format='%(asctime)s] %(filename)s:%(lineno)d %(levelname)s '
                           '- %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

class create_topology(object):
        def __init__(self, create_topo_log_level=None):
            self.logger = logging.getLogger("vnir")
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

            self.number_of_ToRsw = None
            self.number_of_sw = None
            self.number_of_vm = None
            self.total_number_of_vm = None
            self.number_of_pm = None
            self.VM_subnet = None
            self.domain = None
            self.capacity = None
            self.corresponding_PM = None
            self.ip_start = None
            self.ip_end = None
            self.allocated_vm = None
            self.allocated_VLANID = None
            self.available_vm = None
            self.tenant_req = None
            self.vm_array = list()
            self.dir_config = '../ns-allinone-3.29/ns-3.29/'
            self.file_name = 'example.csv'

        def build(self):
            pass

        def initiate_tree_topology(self):
            responce = input('Do you want to visualize topology [y/n] ? ')
            if responce == 'y':
                os.system("cd ../ns-allinone-3.29/ns-3.29/ && ./waf --run new_topo --vis")
            else:
                os.system("cd ../ns-allinone-3.29/ns-3.29/ && ./waf --run new_topo ")
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
                        print(f'Detailed info \n {", ".join(row)}')
                        line_count += 1
                        #print(f'\t{row[0]} works in the {row[1]} department, and was born in {row[2]}.')
                    else:
                        print(f'\t{row[0]}  \t\t{row[1]}   \t{row[2]}  \t\t{row[3]}    \t\t{row[4]} \t{row[5]}')
                        line_count += 1
                self.total_number_of_vm = (line_count-1) * int(row[2])
                # print(f'Processed {line_count} lines.')
                time.sleep(1)
                message = " vm_info parsed"
                self.logger.info(message)

        def get_tenant_request(self):
            sum = 0
            self.vm_array.clear()
            number = input("Enter the number of VN : ")
            print('Enter number of VM required in each VN : ')
            for i in range(int(number)):
                n = input("VN "+str(i+1)+" : ")
                sum = sum + int(n)
                self.vm_array.append(int(n))
            print('Tenant requested : ', self.vm_array)
            if sum > self.total_number_of_vm:
                print("Excceds the total capacity !! Try Again !!!")
                self.get_tenant_request()
            time.sleep(1)

            # tenant_req = input("Input tenant requirement : ")

        def greedy_vm_selection(self):
            message = " Performing greedy search for locating vm"
            self.logger.info(message)

        def short_path_vm_selection(self):
            message = " Performing short_path search for locating vm"
            self.logger.info(message)

if __name__ == '__main__':
        parser = argparse.ArgumentParser(
            description='Process commandline arguments and override configurations in jox_config.json')
        parser.add_argument('--log', metavar='[level]', action='store', type=str,
                            required=False, default='debug',
                            help='set the log level: debug, info (default), warning, error, critical')
        args = parser.parse_args()

        topo = create_topology(args.log)
        topo.initiate_tree_topology()
        # topo.parse_vm_info()
        topo.get_tenant_request()
        topo.greedy_vm_selection()