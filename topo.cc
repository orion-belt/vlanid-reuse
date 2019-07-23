/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */
//maintainer - kharade.rohan@yahoo.com

#include <iostream>
#include <fstream>
#include <string>
#include <chrono>
#include "ns3/gnuplot.h"
#include "ns3/core-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/network-module.h"
#include "ns3/applications-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/csma-module.h"
#include "ns3/internet-module.h"
#include "ns3/internet-apps-module.h"        //  V4PingHelper
#include "ns3/tap-bridge-module.h"           //TAP Interface
#include "ns3/ipv4-static-routing-helper.h"  //V4 Static routes
#include "ns3/ipv4-global-routing-helper.h"  //V4 global routes
#include "ns3/rng-seed-manager.h"    // Seed for RNG
#include "ns3/flow-monitor-module.h"
#include "ns3/sta-wifi-mac.h"

using namespace ns3;
NS_LOG_COMPONENT_DEFINE ("topo");

int
main (int argc, char *argv[])
{
	uint32_t payloadSize1 = 5472;                       // Transport layer payload size in bytes.
	std::string dataRate = "0.5Mbps";                  // Application layer datarate.
	std::string phyRate = "HtMcs7";                    // Physical layer bitrate.
	Packet::EnablePrinting();
	bool verbose = true;
	bool tracing = true;
	CommandLine cmd;
	cmd.AddValue ("payloadSize", "Payload size in bytes", payloadSize1);
	cmd.AddValue ("dataRate", "Application data ate", dataRate);
	cmd.AddValue ("phyRate", "Physical layer bitrate", phyRate);
	cmd.AddValue ("verbose", "Tell echo applications to log if true", verbose);
	cmd.AddValue ("tracing", "Enable pcap tracing", tracing);
	cmd.Parse (argc,argv);
	if (verbose)
		{
		LogComponentEnable ("topo", LOG_LEVEL_INFO);
		//LogComponentEnable ("GlobalRoutingHelper", LOG_LEVEL_ALL);
		LogComponentEnable ("GlobalRouteManagerImpl", LOG_LEVEL_LOGIC);
		}

		int number_of_ToR_sw = 1;
	  int number_of_sw = 1;
		int number_of_VM = 1;

		std::chrono::steady_clock::time_point begin;
		std::chrono::steady_clock::time_point end;
//***********************************************---Creating nodes---*****************************************************s
		begin = std::chrono::steady_clock::now();

		NS_LOG_INFO ("Create nodes.");
		//Create ToR switch node - create "number_of_ToR_sw" nodes for each switch
		NodeContainer ToR_sw_nodes;
		ToR_sw_nodes.Create (number_of_ToR_sw);

		//create SW nodes - create "number_of_	sw * number_of_ToR_sw" nodes for each switch
		NodeContainer sw_nodes;
		sw_nodes.Create (number_of_sw*number_of_ToR_sw);

		//Create vm node - create "number_of_VM * number_of_sw * number_of_ToR_sw" nodes for each switch
		NodeContainer vm_nodes;
		vm_nodes.Create (number_of_VM*number_of_sw*number_of_ToR_sw);

		//Create gw node 
		NodeContainer gw;
		gw.Create (1);

		NodeContainer net_ToR_sw(ToR_sw_nodes.Get(0)) ; //net_ToR_sw is a container for all ToR sw in the network, used to set their position on a grid.
		for(int i = 1;i<number_of_ToR_sw;i++)
		{
			net_ToR_sw.Add(ToR_sw_nodes.Get(i));
		};

		NodeContainer net_sw(sw_nodes.Get(0)) ; //net_sw is a container for all sw in the network, used to set their position on a grid.
		for(int i = 1;i<number_of_sw*number_of_ToR_sw;i++)
		{
			net_sw.Add(sw_nodes.Get(i));
		};

		NodeContainer net_vm(vm_nodes.Get(0 )) ; //net_vm is a container for all vm in the network, used to set their position on a grid.
		for(int i = 1;i<number_of_sw*number_of_ToR_sw*number_of_VM;i++)
		{
			net_vm.Add(vm_nodes.Get(i));
		};

		std::vector<NodeContainer> net_sw_ToRsw; //net_sw_ToRsw is a container, to group nodes -- > sw and ToR_sw
		for(int i=0;i<number_of_ToR_sw;i++)
			{
				for(int j = 0;j<number_of_sw;j++)
				{
				NodeContainer net1 (sw_nodes.Get((i*number_of_sw) +j), ToR_sw_nodes.Get(i));
				net_sw_ToRsw.insert(net_sw_ToRsw.end(), net1);
				}
			}

		std::vector<NodeContainer> net_vm_sw; //net_vm_sw is a container, to group nodes -- > vm and sw
		for(int i=0;i<number_of_sw*number_of_ToR_sw;i++)
			{
				for(int j = 0;j<number_of_VM;j++)
				{
				NodeContainer net2 (vm_nodes.Get((i*number_of_VM) +j), sw_nodes.Get(i));
				net_vm_sw.insert(net_vm_sw.end(), net2);
				}
			}

		std::vector<NodeContainer> net_ToRsw_gw; //net_vm_sw is a container, to group nodes -- > vm and sw
		for(int i=0;i<number_of_ToR_sw;i++)
			{
				// for(int j = 0;j<number_of_VM;j++)
				// {
				NodeContainer net_gw (gw.Get(0), ToR_sw_nodes.Get(i));
				net_ToRsw_gw.insert(net_ToRsw_gw.end(), net_gw);
				// }
			}

		end= std::chrono::steady_clock::now();
		NS_LOG_ERROR("Time required for node creation = " << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count() <<" NanoSec");
		begin = std::chrono::steady_clock::now();

		//each nodecontainer of vector netvm has all the vms connected to one sw. - total number_of_ToR_sw*number_of_sw netcontainers
		// std::vector<NodeContainer>netvm;
		// for(int i = 0; i<number_of_sw*number_of_ToR_sw; i++)
		// {
		// 	NodeContainer net3(vm_nodes.Get(i*number_of_VM )) ;
		// 	for(int j = 1;j<number_of_VM;j++)
		// 	{
		// 	net3.Add(vm_nodes.Get(i*number_of_VM +j));
		// 	}
		// 	netvm.insert(netvm.end(), net3);
		// }
			end= std::chrono::steady_clock::now();
			NS_LOG_ERROR("Time required for node containers = " << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count() <<" NanoSec");


	begin = std::chrono::steady_clock::now();
	double errRate = 0.00000001;
	DoubleValue rate (errRate);
	Ptr<RateErrorModel> em1 =
	CreateObjectWithAttributes<RateErrorModel> ("RanVar", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=1.0]"), "ErrorRate", rate);
	  //create p2p channels
	NS_LOG_INFO ("Create p2p channels.");
	PointToPointHelper p2p;
	p2p.SetDeviceAttribute ("DataRate", StringValue ("4000Mbps"));
	p2p.SetChannelAttribute ("Delay", StringValue ("2ms"));

	// There are a total of number_of_sw*number_of_sw APs, so there are a total of number_of_sw*number_of_sw netdevice containers
	std::vector<NetDeviceContainer> ndc_sw_ToRsw;
	for(int i = 0;i<number_of_sw*number_of_ToR_sw;i++)
	  {
	  NetDeviceContainer ndc1 = p2p.Install (net_sw_ToRsw[i]); //switch and ToR_switch
	  ndc_sw_ToRsw.insert(ndc_sw_ToRsw.end(), ndc1);
	  ndc1.Get(0)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));
	  ndc1.Get(1)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));
	  }
	
	std::vector<NetDeviceContainer> ndc_vm_sw;
	for(int i = 0;i<number_of_sw*number_of_ToR_sw*number_of_VM;i++)
	  {
	  NetDeviceContainer ndc2 = p2p.Install (net_vm_sw[i]); //vm and switch
	  ndc_vm_sw.insert(ndc_vm_sw.end(), ndc2);
	  ndc2.Get(0)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));
	  ndc2.Get(1)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));
	  }

	std::vector<NetDeviceContainer> ndc_ToRsw_gw;
	for(int i = 0;i<number_of_ToR_sw;i++)
	  {
	  NetDeviceContainer ndc3 = p2p.Install (net_ToRsw_gw[i]); //ToR_switch and gw
	  ndc_ToRsw_gw.insert(ndc_ToRsw_gw.end(), ndc3);
	  ndc3.Get(0)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));
	  ndc3.Get(1)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));
	  }	
	end= std::chrono::steady_clock::now();
	NS_LOG_ERROR("Time required for P2P install = " << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count() <<" NanoSec");
	
//***********************************************  Set position of nodes **************************************
			begin = std::chrono::steady_clock::now();
			MobilityHelper mobility_gw;
			mobility_gw.SetPositionAllocator ("ns3::GridPositionAllocator",
																			"MinX", DoubleValue (50.0),
																			"MinY", DoubleValue (-70.0),
																			"DeltaX", DoubleValue (80.0),
																			"DeltaY", DoubleValue (10.0),
																			"GridWidth", UintegerValue (100),
																			"LayoutType", StringValue ("RowFirst"));
			mobility_gw.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
			mobility_gw.Install (gw);	
		
			MobilityHelper mobility_ToR;
			mobility_ToR.SetPositionAllocator ("ns3::GridPositionAllocator",
																			"MinX", DoubleValue (25.0),
																			"MinY", DoubleValue (-50.0),
																			"DeltaX", DoubleValue (80.0),
																			"DeltaY", DoubleValue (10.0),
																			"GridWidth", UintegerValue (100),
																			"LayoutType", StringValue ("RowFirst"));
			mobility_ToR.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
			mobility_ToR.Install (net_ToR_sw);	

			MobilityHelper mobility_sw;
			mobility_sw.SetPositionAllocator ("ns3::GridPositionAllocator",
																			"MinX", DoubleValue (-5.0),
																			"MinY", DoubleValue (-20.0),
																			"DeltaX", DoubleValue (20.0),
																			"DeltaY", DoubleValue (10.0),
																			"GridWidth", UintegerValue (1000),
																			"LayoutType", StringValue ("RowFirst"));
			mobility_sw.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
			mobility_sw.Install (net_sw);

		MobilityHelper mobility_vm;
		mobility_vm.SetPositionAllocator ("ns3::GridPositionAllocator",
																		"MinX", DoubleValue (-10.0),
																		"MinY", DoubleValue (1.00),
																		"DeltaX", DoubleValue (10.0),
																		"DeltaY", DoubleValue (5.0),	
																		"GridWidth", UintegerValue (10),
																		"LayoutType", StringValue ("ColumnFirst"));
		mobility_vm.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
		mobility_vm.Install(net_vm);
		end= std::chrono::steady_clock::now();
		std::cout << "Time required for positioning of nodes = " << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count() <<" NanoSec"<<std::endl;

		//*********************************************** IP Stack **************************************
		begin = std::chrono::steady_clock::now();

		InternetStackHelper stack;

		for(int i = 0;i<number_of_sw*number_of_ToR_sw;i++)
		{
		stack.Install (sw_nodes.Get(i));
		}
		for(int i = 0 ;i <number_of_ToR_sw;i++)
		{
			stack.Install (ToR_sw_nodes.Get(i));
		}
	//	stack.Install (ctl);
		for(int i=0;i<number_of_sw*number_of_VM*number_of_ToR_sw;i++)
		{
			stack.Install (vm_nodes.Get(i));
		}
		stack.Install (gw);

		NS_LOG_INFO ("Added ip stack.");

		NS_LOG_INFO ("Assigning IPv4 Addresses.");
		Ipv4AddressHelper ipv4;


		ipv4.SetBase (Ipv4Address ("192.168.0.0"), Ipv4Mask ("255.255.0.0"));
		for(int i = 0;i<number_of_ToR_sw;i++)
		{
			Ipv4InterfaceContainer iic2 = ipv4.Assign (ndc_ToRsw_gw[i]);  //ToRswitch and Gateway
		}

		ipv4.SetBase (Ipv4Address ("10.0.0.0"), Ipv4Mask ("255.255.0.0"));
		std::vector<Ipv4InterfaceContainer> iic_ap_sw;
		for(int i = 0; i<number_of_sw*number_of_ToR_sw;i++)
		{
			Ipv4InterfaceContainer iic1 = ipv4.Assign (ndc_sw_ToRsw[i]);  //switch and ToRsw
			iic_ap_sw.insert(iic_ap_sw.end(), iic1);
		}

		std::string a = "20.";
		for(int i = 0; i<number_of_sw*number_of_ToR_sw; i++)
		{
			int b = (i/250) +1;
			std::string b_str = std::to_string(b);
			int ip_c = (i%250);
			std::string c_str  =std::to_string(ip_c);
			std::string nw_ending = ".0";
			std::string d = a+b_str+"."+c_str+ nw_ending;

			const char * c = d.c_str();
			ipv4.SetBase (Ipv4Address (c), Ipv4Mask ("255.255.255.0"));
	    std::vector<Ipv4InterfaceContainer> iic_vm_sw;
			 for (int j=0;j<number_of_VM; j++)
			 {
				Ipv4InterfaceContainer iic3 = ipv4.Assign (ndc_vm_sw[(i*number_of_VM) +j]);  //switch and vm
			 }

			// iic_vm_sw.insert(iic_vm_sw.end(), iic3);

		}
				end= std::chrono::steady_clock::now();
				NS_LOG_ERROR("Time required for IP stack install and IP addressing = " << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count() <<" NanoSec");


//**********************************---< IPv4 routing >---**************************************
		    begin = std::chrono::steady_clock::now();
	  	  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();   // Global Routing


	  	/* Static routing
	  	we use static routing to reduce the time it takes to populate the route
	  	*/

// 	  	//Static routes for stations - the gateway for all stations is the corresponding AP the station is connected to
// 	  		std::string sta_gw_ip_start = "10.";
// 	  		std::string sta_gw_ip_end = ".1";
// 	  		for(int i =0;i<number_of_sw*number_of_ToR_sw;i++)
// 	  		{
// 	  				for(int j=0;j<number_of_VM;j++)
// 	  			{
// 	  					int gw_ip_b = (i/250) +1;
// 	  					std::string gw_ip_b_str = std::to_string(gw_ip_b);
// 	  					int gw_ip_c = (i%250);
// 	  					std::string gw_ip_c_str  =std::to_string(gw_ip_c);
// 	  					std::string gw_ip_addr = sta_gw_ip_start+gw_ip_b_str+"."+gw_ip_c_str+ sta_gw_ip_end;
// 	  					const char *gw_ip = gw_ip_addr.c_str();
// //
// //	  					  Ipv4Address STAaddr =  vm_nodes.Get((i*number_of_VM) +j)->GetObject<Ipv4> ()->GetAddress (1, 0).GetLocal ();
// //	  		  			  NS_LOG_ERROR((i*number_of_VM) +j<<" "<<STAaddr<<" "<<gw_ip<<" ");

// 	  				Ptr<Ipv4> ipv4STA = vm_nodes.Get((i*number_of_VM) +j)->GetObject<Ipv4> ();            // Static Routing
// 	  				Ipv4StaticRoutingHelper STA;
// 	  				Ptr<Ipv4StaticRouting> staticSTA = STA.GetStaticRouting (ipv4STA);
// 	  				staticSTA->AddNetworkRouteTo (Ipv4Address ("192.169.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
// 	  				staticSTA->AddNetworkRouteTo (Ipv4Address ("192.168.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
// 	  				//staticSTA1->AddNetworkRouteTo (Ipv4Address ("10.0.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
// 	  			}
// 	  		}

// 	  	 	//Static routes for AP
// 	  		 std::string ap_gw_ip_start = "10.0";
// 	  		 int ip_d = 0;
// 	  	     for(int i =0; i<number_of_ToR_sw;i++)
// 	  	     {
// 	  				for(int j=0;j<number_of_sw;j++)
// 	  			{
// 	  					int c;

// 	  					if (j == 254)
// 	  					{
// 	  						c = 1;
// 	  					}
// 	  					else
// 	  					{
// 	  				    c = (j/127);
// 	  					}
// 	  				//	NS_LOG_ERROR(c<<" "<<i*number_of_sw+j);
// 	  					std::string c_str = std::to_string(c);
// 	  					//int ip_d = ((i%250)+2);

// 	  					if (ip_d < 254)
// 	  					{
// 	  					ip_d = ip_d + 2;
// 	  					}
// 	  					else{
// 	  						ip_d = 0;
// 	  					    }
// 	  					std::string d_str =std::to_string(ip_d);
// 	  					std::string d = ap_gw_ip_start+"."+c_str+"."+d_str ;
// 	  					const char *gw_ip = d.c_str();

// 	  	//			     Ipv4Address Apaddr = sw_nodes.Get(i*number_of_sw+j)->GetObject<Ipv4> ()->GetAddress (1, 0).GetLocal ();
// 	  	//				 NS_LOG_ERROR(i*number_of_sw+j<<" "<<Apaddr<<" "<<gw_ip<<" ");

// 	  	 		 Ptr<Ipv4> ipv4AP1 = sw_nodes.Get(i*number_of_sw+j)->GetObject<Ipv4> ();
// 	  	 		// NS_LOG_ERROR(i*number_of_sw+j<<" "<<gw_ip);
// 	  	   	     Ipv4StaticRoutingHelper AP1;
// 	  	    	 Ptr<Ipv4StaticRouting> staticAP1 = AP1.GetStaticRouting (ipv4AP1);
// 	  	    	 staticAP1->AddNetworkRouteTo (Ipv4Address ("192.169.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
// 	  	    	 staticAP1->AddNetworkRouteTo (Ipv4Address ("192.168.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
// 	  	    	// NS_LOG_ERROR(gw_ip);
// 	  	       }
// 	  		}

// 		  	 	//Static routes for Switches
// 	  		std::string nxt_hop_ip_start = "10.";
// 	  		std::string nxt_hop_ip_end = ".0";
// 	  		int nxt_hop_c = 0;
// 	  		std::string sw_gw_ip_start = "10.0";
// 	  	    ip_d = 1;
// 	  	    for(int i = 0; i<number_of_ToR_sw;i++)
// 	  	     {
// 	  	       for(int j=0;j<number_of_sw;j++)
// 	  			{
// 	  				int nxt_hop_b = ((i*number_of_sw+j)/250+1);
// 	  			    std::string nxt_hop_b_str = std::to_string(nxt_hop_b);
// 	  				// std::string nxt_hop_c_str = std::to_string(nxt_hop_c);
// 	  				 std::string nxt_hop_c_str;// = std::to_string(nxt_hop_c);


// 	  					 std::string d_str =std::to_string(ip_d);
// 	  					if (ip_d <= 253)
// 	  					{
// 	  					ip_d +=2;
// 	  					}
// 	  					else{
// 	  						ip_d = 1;
// 	  					}

// 	  					if (nxt_hop_c < 250)
// 	  								{
// 	  						 	 	 nxt_hop_c_str = std::to_string(nxt_hop_c);
// 	  								 nxt_hop_c +=1;
// 	  								}
// 	  								else{

// 	  									 nxt_hop_c = 0;
// 	  									 nxt_hop_c_str = std::to_string(nxt_hop_c);
// 	  									 nxt_hop_c +=1;
// 	  								}
// 	  					std::string nxt_hop_sw = nxt_hop_ip_start+nxt_hop_b_str+"."+ nxt_hop_c_str+nxt_hop_ip_end;
// 	  					const char *nxt_hop =nxt_hop_sw.c_str();

// 	  					int gw_ip_c = ((i*number_of_sw+j)/128);
// 	  					std::string gw_ip_c_str = std::to_string(gw_ip_c);
// 	  					std::string gw_ip_nw= sw_gw_ip_start+"."+gw_ip_c_str+"."+d_str ;
// 	  					const char *gw_ip = gw_ip_nw.c_str();


// 	  	////
// 	  	//				Ipv4Address SWaddr1 = sw_nodes.Get(i)->GetObject<Ipv4> ()->GetAddress (j+1, 0).GetLocal ();
// 	  	//			   NS_LOG_ERROR(j<<" "<<SWaddr1<<" "<<gw_ip<<" "<<nxt_hop<<" ");

// 	  	     Ptr<Ipv4> ipv4SW1 = ToR_sw_nodes.Get(i)->GetObject<Ipv4> ();            // Static Routing
// 	  	     Ipv4StaticRoutingHelper SW1;
// 	  	     Ptr<Ipv4StaticRouting> staticSW1 = SW1.GetStaticRouting (ipv4SW1);
// 	  	     staticSW1->AddNetworkRouteTo (Ipv4Address (nxt_hop),Ipv4Mask("255.255.255.0"), Ipv4Address (gw_ip),j+1);
// 	  		//  staticSW1->AddNetworkRouteTo (Ipv4Address ("10.1.1.0"),Ipv4Mask("255.255.255.0"), Ipv4Address ("10.0.0.3"), 2);




// 	        	}
// 	  	        Ptr<Ipv4> ipv4SW1 = ToR_sw_nodes.Get(i)->GetObject<Ipv4> ();            // Static Routing
// 	  	        Ipv4StaticRoutingHelper SW1;
// 	  	       Ptr<Ipv4StaticRouting> staticSW1 = SW1.GetStaticRouting (ipv4SW1);

// 	  	  	   //Ipv4Address CTLaddr = ctl->GetObject<Ipv4> ()->GetAddress (i+1, 0).GetLocal ();
// 	  	       //staticSW1->AddNetworkRouteTo (Ipv4Address ("192.169.0.0"),Ipv4Mask("255.255.0.0"), CTLaddr,(number_of_sw+1));
// 	  	 	   //NS_LOG_ERROR(number_of_sw+1<<" "<<CTLaddr);
// 	  		 }


// //	  	     int gw_ip_end =1;
// 	  		 nxt_hop_c = 0;
// //	  		 std::string GW_gw_ip_start = "192.169.";

// 	  	 	for(int i = 0; i<number_of_ToR_sw;i++)
// 	  	     {
// 	  	       for(int j=0;j<number_of_sw;j++)
// 	  			{
// 	  				int nxt_hop_b = ((i*number_of_sw+j)/250+1);
// 	  			    std::string nxt_hop_b_str = std::to_string(nxt_hop_b);
// 	  				// std::string nxt_hop_c_str = std::to_string(nxt_hop_c);
// 	  			    std::string nxt_hop_c_str;// = std::to_string(nxt_hop_c);

// 	  				if (nxt_hop_c < 250)
// 	  								{
// 	  						 	 	 nxt_hop_c_str = std::to_string(nxt_hop_c);
// 	  								 nxt_hop_c +=1;
// 	  								}
// 	  								else{
// 	  									 nxt_hop_c = 0;
// 	  									 nxt_hop_c_str = std::to_string(nxt_hop_c);
// 	  									 nxt_hop_c +=1;
// 	  								}


// 	  					std::string nxt_hop_nw_ip = nxt_hop_ip_start+nxt_hop_b_str+"."+ nxt_hop_c_str+nxt_hop_ip_end;
// 	  				//	const char *nxt_hop =nxt_hop_nw_ip.c_str();

// //	  					int gw_ip_c = (i/128);
// //	  							std::string gw_ip_c_str = std::to_string(gw_ip_c);
// //
// //	  							std::string gw_ip_d_str;
// //	  					     	if (gw_ip_end > 255)
// //	  							  	   {
// //	  									gw_ip_end = 1;
// //	  									std::to_string(gw_ip_end);
// //	  							  	   }
// //	  							gw_ip_d_str =std::to_string(gw_ip_end);
// //	  							std::string d= GW_gw_ip_start+gw_ip_c_str+"."+gw_ip_d_str ;
// //	  							const char *gw_ip = d.c_str();
//      	//
// 	  	//				Ipv4Address GWaddr = gw->GetObject<Ipv4> ()->GetAddress (i+1, 0).GetLocal ();
// 	  	//			    NS_LOG_ERROR(i+1<<" Interface "<<GWaddr<<" GW "<<gw_ip<<" ,Ntx Hop "<<nxt_hop);



// 	  		// Ptr<Ipv4> ipv4GW1 = gw->GetObject<Ipv4> ();            // Static Routing
// 	  	     //Ipv4StaticRoutingHelper GW1;
// 	  	    // Ptr<Ipv4StaticRouting> staticGW1 = GW1.GetStaticRouting (ipv4GW1);
// 	  		 //staticGW1->AddNetworkRouteTo (Ipv4Address (nxt_hop),Ipv4Mask("255.255.255.0"), Ipv4Address ("192.169.0.1"),1);
// 	  		 //staticGW1->AddNetworkRouteTo (Ipv4Address ("10.0.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address ("192.169.0.1"),1);

// 	  		//nxt_hop = 10.1.j.0

// 	  			}
// 	  			}


// 	  	 	int gw_ip_end=1;
// 	  	     nxt_hop_c = 0;
// 	  	     std::string CTL_gw_ip_start = "192.168.";

// 	  	 	for(int i = 0; i<number_of_ToR_sw;i++)
// 	  	     {
// 	  	       for(int j=0;j<number_of_sw;j++)
// 	  			{
// 	  	    	    int nxt_hop_b = ((i*number_of_sw+j)/250+1);
// 	  			    std::string nxt_hop_b_str = std::to_string(nxt_hop_b);
// 	  			    std::string nxt_hop_c_str;// = std::to_string(nxt_hop_c);
// 	  				  if (nxt_hop_c < 250)
// 	  							{
// 	  								 nxt_hop_c_str = std::to_string(nxt_hop_c);
// 	  								 nxt_hop_c +=1;
// 	  							}
// 	  					else    {
// 	  								 nxt_hop_c = 0;
// 	  								 nxt_hop_c_str = std::to_string(nxt_hop_c);
// 	  								 nxt_hop_c +=1;
// 	  							}
// 	  					std::string nxt_hop_ip = nxt_hop_ip_start+nxt_hop_b_str+"."+ nxt_hop_c_str+nxt_hop_ip_end;
// 	  				//	const char *nxt_hop =nxt_hop_ip.c_str();

// 	  					int gw_ip_c = (i/128);
// 	  					std::string gw_ip_c_str = std::to_string(gw_ip_c);

// 	  					std::string gw_ip_d_str;
// 	  			     	if (gw_ip_end > 255)
// 	  					  	   {
// 	  							gw_ip_end = 1;
// 	  							std::to_string(gw_ip_end);
// 	  					  	   }
// 	  					gw_ip_d_str =std::to_string(gw_ip_end);
// 	  					std::string d= CTL_gw_ip_start+gw_ip_c_str+"."+gw_ip_d_str ;
// 	  	//				const char *gw_ip = d.c_str();

// 	  	//				Ipv4Address CTLaddr = ctl->GetObject<Ipv4> ()->GetAddress (i+1, 0).GetLocal ();
// 	  	//			    NS_LOG_ERROR(i+1<<" Interface "<<CTLaddr<<" GW "<<gw_ip<<" ,Ntx Hop "<<nxt_hop);

// 	  		//  Ptr<Ipv4> ipv4CTL = ctl->GetObject<Ipv4> ();            // Static Routing
// 	  	  //    Ipv4StaticRoutingHelper CTL;
// 	  	  //    Ptr<Ipv4StaticRouting> staticCTL = CTL.GetStaticRouting (ipv4CTL);
// 	  		//  staticCTL->AddNetworkRouteTo (Ipv4Address (nxt_hop),Ipv4Mask("255.255.255.0"), Ipv4Address (gw_ip), i+1);
// 	  		 //nxt_hop = 10.1.j.0
// 	  			}
// 	  	       gw_ip_end +=2;
// 	  			}


// 	  	 				end= std::chrono::steady_clock::now();
// 	  	 			    NS_LOG_ERROR("Time required for Static Routing = " << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count() <<" NanoSec");


	  	 				end= std::chrono::steady_clock::now();
	  	 			    NS_LOG_ERROR("Time required for Global Routing = " << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count() <<" NanoSec");

		double endtime = 1;
		Simulator::Stop (Seconds (endtime));
		Simulator::Run ();	
  return 0;
}
