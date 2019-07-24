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
//SDN
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

int
main (int argc, char *argv[])
{
	uint32_t payloadSize1 = 5472;                       // Transport layer payload size in bytes.
	std::string dataRate = "0.5Mbps";                  // Application layer datarate.
	std::string tcpVariant = "ns3::TcpNewReno";        // TCP variant type.
	std::string phyRate = "HtMcs7";                    // Physical layer bitrate.
	Packet::EnablePrinting();
	bool verbose = true;
	bool tracing = true;

	CommandLine cmd;
	cmd.AddValue ("payloadSize", "Payload size in bytes", payloadSize1);
	cmd.AddValue ("dataRate", "Application data ate", dataRate);
	cmd.AddValue ("tcpVariant", "Transport protocol to use: TcpTahoe, TcpReno, TcpNewReno, TcpWestwood, TcpWestwoodPlus ", tcpVariant);
	cmd.AddValue ("phyRate", "Physical layer bitrate", phyRate);
	cmd.AddValue ("verbose", "Tell echo applications to log if true", verbose);
	cmd.AddValue ("tracing", "Enable pcap tracing", tracing);
	cmd.Parse (argc,argv);
//Verbose?
	if (verbose)
		{
		  //LogComponentEnable ("UdpEchoClientApplication", LOG_LEVEL_ERROR);
		  //LogComponentEnable ("UdpEchoServerApplication", LOG_LEVEL_INFO);
		//  LogComponentEnable ("CsmaNetDevice", LOG_LEVEL_INFO);
		//  LogComponentEnable ("ApWifiMac", LOG_LEVEL_WARN);
		//  LogComponentEnable ("StaWifiMac", LOG_LEVEL_WARN);
		//  LogComponentEnable ("WifiNetDevice", LOG_LEVEL_WARN);
		//  LogComponentEnable ("VirtualNetDevice", LOG_LEVEL_WARN);
		//  LogComponentEnable ("NetDevice", LOG_LEVEL_WARN);
		//  LogComponentEnable ("PointToPointNetDevice", LOG_LEVEL_WARN);
		 //LogComponentEnable ("topo", LOG_LEVEL_ERROR);
		//  LogComponentEnable ("Ipv4AddressHelper", LOG_LEVEL_ERROR);
		//  LogComponentEnable ("YansWifiChannel", LOG_LEVEL_ERROR);
		//  LogComponentEnable("ApWifiMac", LOG_LEVEL_WARN);
		}
	std::ofstream myfile;
	std::ofstream throughput_file_handler;
	std::ofstream pkt_delay_file_handler;
	std::ofstream set_up_time_file_handler;

		int number_of_STA = 2;
	    int number_of_AP = 2;
		int number_of_sw = 1;
		std::chrono::steady_clock::time_point begin;
		std::chrono::steady_clock::time_point end;
//***********************************************---Creating pointer nodes---*****************************************************s
		//First create AP nodes - create "number_of_AP" nodes for each switch
		NodeContainer ap_nodes;
		ap_nodes.Create (number_of_AP*number_of_sw);
		NodeContainer net_ap(ap_nodes.Get(0 )) ; //net_ap is a container for all ap in the network, used to set their position on a grid.
		for(int i = 1;i<number_of_AP*number_of_sw;i++)
		{
			net_ap.Add(ap_nodes.Get(i));
		}

		//Then create a gateway, switch and controller node
		Ptr<Node> gw = CreateObject<Node> ();
		//Names::Add ("Gateway", gw);
		//Create switch node
		NodeContainer sw_nodes;
		sw_nodes.Create (number_of_sw);

		//Create the controller node
		Ptr<Node> ctl = CreateObject<Node> ();
		//Names::Add ("SDN Conroller", ctl);
		//create station nodes
		NodeContainer sta_nodes;
		sta_nodes.Create (number_of_STA*number_of_AP*number_of_sw);

		//Create node containers, to group nodes
		std::vector<NodeContainer> netap_sw;
		for(int i=0;i<number_of_sw;i++)
			{
				for(int j = 0;j<number_of_AP;j++)
				{
				NodeContainer net1 (ap_nodes.Get((i*number_of_AP) +j), sw_nodes.Get(i));
				netap_sw.insert(netap_sw.end(), net1);
				}
			}
		std::vector<NodeContainer> netsw_ctl; //each nodecontainer is a pair of switch-controller. total number_of_sw nodecontainers
		for(int i=0;i<number_of_sw;i++)
		{
			NodeContainer net2 (sw_nodes.Get(i), ctl);
			netsw_ctl.insert(netsw_ctl.end(), net2);

		}

		//each nodecontainer of vector netsta has all the stations connected to one ap. - total number_of_sw*number_of_AP netcontainers
		std::vector<NodeContainer> netsta;

		for(int i = 0; i<number_of_AP*number_of_sw; i++)
		{
			NodeContainer net3(sta_nodes.Get(i*number_of_STA )) ;
			for(int j = 1;j<number_of_STA;j++)
			{
			net3.Add(sta_nodes.Get(i*number_of_STA +j));
			}
			netsta.insert(netsta.end(), net3);
		}
	double errRate = 0.00000001;
	DoubleValue rate (errRate);
	Ptr<RateErrorModel> em1 =
	CreateObjectWithAttributes<RateErrorModel> ("RanVar", StringValue ("ns3::UniformRandomVariable[Min=0.0|Max=1.0]"), "ErrorRate", rate);
	  //create channels
		PointToPointHelper p2p;
		p2p.SetDeviceAttribute ("DataRate", StringValue ("4000Mbps"));
		p2p.SetChannelAttribute ("Delay", StringValue ("2ms"));
		PointToPointHelper p2p_whitespace;
		p2p_whitespace.SetDeviceAttribute ("DataRate", StringValue ("40Mbps"));
		p2p_whitespace.SetChannelAttribute ("Delay", StringValue ("2ms"));

	  //Adding netdevice container to all the switch-ap pairs.
	  // There are a total of number_of_AP*number_of_sw APs, so there are a total of number_of_AP*number_of_sw netdevice containers
	  std::vector<NetDeviceContainer> ndcap_sw;
	for(int i = 0;i<number_of_AP*number_of_sw;i++)
	  {
	  NetDeviceContainer ndc1 = p2p_whitespace.Install (netap_sw[i]); //ap and switch
	  ndcap_sw.insert(ndcap_sw.end(), ndc1);
	  ndc1.Get(0)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));
	  ndc1.Get(1)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));

	  }
	  std::vector<NetDeviceContainer>ndcsw_ctl;
	  std::vector<NetDeviceContainer>ndcsw_gw;
	for (int i = 0; i<number_of_sw;i++)
	{
	   NetDeviceContainer ndc2 = p2p.Install (netsw_ctl[i]); //switch and controller
		ndcsw_ctl.insert(ndcsw_ctl.end(), ndc2);
		ndc2.Get(0)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));
	    ndc2.Get(1)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));

	 // NetDeviceContainer ndc5 = p2p.Install (netsw_gw[i]); //switch and gateway
	 // ndcsw_gw.insert(ndcsw_gw.end(), ndc5);
	}
	 //@@@@@@@@@@@@ added
	 NodeContainer net4 (ctl, gw) ;               //Controller and gateway
	 NetDeviceContainer ndc5 = p2p.Install (net4);
	 ndc5.Get(0)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));
	 ndc5.Get(1)->SetAttribute ("ReceiveErrorModel", PointerValue (em1));

//create wifi channel
		/* No fragmentation and no RTS/CTS */
		Config::SetDefault ("ns3::WifiRemoteStationManager::FragmentationThreshold", StringValue ("999999"));
		Config::SetDefault ("ns3::WifiRemoteStationManager::RtsCtsThreshold", StringValue ("999999"));

		std::vector<YansWifiChannelHelper> ywch;
		std::vector<YansWifiPhyHelper> ywph;
		std::vector<NetDeviceContainer>ndc_sta;
		std::vector<NetDeviceContainer>ndc_ap_sta;
		for(int i = 0; i<number_of_sw;i++)
		{
			for(int j = 0; j<number_of_AP;j++)
				{
					YansWifiChannelHelper channel1 = YansWifiChannelHelper::Default ();
					YansWifiPhyHelper phy = YansWifiPhyHelper::Default ();
					phy.SetChannel (channel1.Create ());
					WifiHelper wifi;
					wifi.SetStandard(WIFI_PHY_STANDARD_80211n_2_4GHZ);
						//wifi.SetRemoteStationManager ("ns3::AarfWifiManager",);
						wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager","DataMode",StringValue("HtMcs6"),"ControlMode",StringValue("HtMcs0"));
						WifiMacHelper mac;
						Ssid ssid = Ssid ("ns-3-ssid1");
						mac.SetType ("ns3::StaWifiMac",
													"Ssid", SsidValue (ssid),
													"ActiveProbing", BooleanValue (false));
						NetDeviceContainer ndc3 = wifi.Install (phy, mac, netsta[(i*number_of_AP) +j]);//all sta connected to ap j of sw i
						ndc_sta.insert(ndc_sta.end(), ndc3);
						mac.SetType ("ns3::ApWifiMac",
													"Ssid", SsidValue (ssid));
						NetDeviceContainer ndc4 = wifi.Install (phy, mac, ap_nodes.Get((i*number_of_AP) +j));
						ndc_ap_sta.insert(ndc_ap_sta.end(), ndc4);


						ywch.insert(ywch.end(), channel1);
						ywph.insert(ywph.end(), phy);
				}
			}

		//******************************************************************************************

//***********************************************  Set position of wireless nodes **************************************
			 	 begin = std::chrono::steady_clock::now();

		MobilityHelper mobility;
		MobilityHelper mobility1;
		mobility1.SetPositionAllocator ("ns3::GridPositionAllocator",
																		"MinX", DoubleValue (5.0),
																		"MinY", DoubleValue (0.0),
																		"DeltaX", DoubleValue (5.0),
																		"DeltaY", DoubleValue (5.0),
																		"GridWidth", UintegerValue (3),
																		"LayoutType", StringValue ("RowFirst"));
		mobility1.SetMobilityModel ("ns3::ConstantPositionMobilityModel");

		mobility1.Install (net_ap); //put ap on a grid


		for (int i = 0; i < number_of_AP*number_of_sw; ++i)
    {
		Ptr<ListPositionAllocator> WifiStaPosition = CreateObject<ListPositionAllocator> ();
		Ptr<MobilityModel> ap_mobility = net_ap.Get(i)->GetObject<MobilityModel> ();
			Vector pos = ap_mobility->GetPosition();
		for(int j=0;j<number_of_STA;j++)
		{
      int v1 = ((rand() % 61)-30)+(pos.x) +200;
      int v2 = ((rand() % 61)-30)+(pos.y);
       if (pow(v1-pos.x-200,2)+pow(v2-pos.y,2)<=pow(30,2))
         WifiStaPosition->Add (Vector(v1, v2, 0));
       else
         j--;
		}
     // std::cout << " sta1 location1: " << v1-50<< "sta1 location2: "<<v2-30<<" \n";//added
      mobility.SetPositionAllocator(WifiStaPosition);
  mobility1.Install(netsta[i]);
    }
		end= std::chrono::steady_clock::now();
		std::cout << "Time required for positioning of wireless nodes = " << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count() <<" NanoSec"<<std::endl;






//*********************************************** IP Stack **************************************
		InternetStackHelper stack;
		for(int i = 0;i<number_of_AP*number_of_sw;i++)
		{
		stack.Install (ap_nodes.Get(i));
		}
		for(int i = 0 ;i <number_of_sw;i++)
		{
			stack.Install (sw_nodes.Get(i));
		}
		stack.Install (ctl);
		for(int i=0;i<number_of_AP*number_of_STA*number_of_sw;i++)
		{
			stack.Install (sta_nodes.Get(i));
		}

		stack.Install (gw);


		Ipv4AddressHelper ipv4;

		ipv4.SetBase (Ipv4Address ("10.0.0.0"), Ipv4Mask ("255.255.0.0"));

		std::vector<Ipv4InterfaceContainer> iic_ap_sw;
		for(int i = 0; i<number_of_AP*number_of_sw;i++)
		{
                       

			Ipv4InterfaceContainer iic1 = ipv4.Assign (ndcap_sw[i]);  //switch and AP
			iic_ap_sw.insert(iic_ap_sw.end(), iic1);
		}
                

		ipv4.SetBase (Ipv4Address ("192.168.0.0"), Ipv4Mask ("255.255.0.0"));

		for(int i = 0;i<number_of_sw;i++)
		{
			Ipv4InterfaceContainer iic2 = ipv4.Assign (ndcsw_ctl[i]); //switch and controller
		}
		ipv4.SetBase (Ipv4Address ("192.169.0.0"), Ipv4Mask ("255.255.0.0"));

			Ipv4InterfaceContainer iic5 = ipv4.Assign (ndc5);   //switch and Gateway


    //
    //		ipv4.SetBase (Ipv4Address ("192.168.2.0"), Ipv4Mask ("255.255.255.0"));
    //		for(int i = 0;i<number_of_sw;i++)
    //		{
    //			Ipv4InterfaceContainer iic2 = ipv4.Assign (ndcsw_ctl[i]); //switch and controller
    //		}
    //	        ipv4.SetBase (Ipv4Address ("192.168.3.0"), Ipv4Mask ("255.255.255.0"));
    //		 Ipv4InterfaceContainer iic5 = ipv4.Assign (ndc5);   //Controller and Gateway


		std::string a = "10.";
 //			int b = (iteration_number/250) +1;
 //			std::string b_str = std::to_string(b);
			// if(iteration_number<250)
			// 	{
			// 		ip = "192.1.";}
			// 	else if(iteration_number<500)
			// 	{
			// 		ip = "192.2.";
			// 	}
			// 	else if(iteration_number<750)
			// 	{
			// 		ip = "192.3.";
			// 	}
			// 	else
			// 	{
			// 		ip = "192.4.";
			// 	}
		for(int i = 0;i<number_of_AP*number_of_sw;i++)
		{
			int b = (i/250) +1;
			std::string b_str = std::to_string(b);
			int ip_c = (i%250);

			std::string c_str  =std::to_string(ip_c);
			std::string nw_ending = ".0";
			std::string d = a+b_str+"."+c_str+ nw_ending;

			const char * c = d.c_str();
			ipv4.SetBase (Ipv4Address (c), Ipv4Mask ("255.255.255.0"));
			Ipv4InterfaceContainer iic4 = ipv4.Assign (ndc_ap_sta[i]);               //AP
			Ipv4InterfaceContainer iic3 = ipv4.Assign (ndc_sta[i]);                  //Sta
		}

		UdpEchoServerHelper echoServer2 (10);
		ApplicationContainer serverApps2 = echoServer2.Install (ctl);
		serverApps2.Start (Seconds (1.0));


//**********************************---< IPv4 routing >---**************************************
 //	  	  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();   // Global Routing


	  	/* Static routing
	  	we have used static routing to reduce the time it takes for the code to run
	  	*/

	  	//Static routes for stations - the gateway for all stations is the corresponding AP the station is connected to
	  		std::string sta_gw_ip_start = "10.";
	  		std::string sta_gw_ip_end = ".1";
	  		for(int i =0;i<number_of_AP*number_of_sw;i++)
	  		{
	  				for(int j=0;j<number_of_STA;j++)
	  			{
	  					int gw_ip_b = (i/250) +1;
	  					std::string gw_ip_b_str = std::to_string(gw_ip_b);
	  					int gw_ip_c = (i%250);
	  					std::string gw_ip_c_str  =std::to_string(gw_ip_c);
	  					std::string gw_ip_addr = sta_gw_ip_start+gw_ip_b_str+"."+gw_ip_c_str+ sta_gw_ip_end;
	  					const char *gw_ip = gw_ip_addr.c_str();
 //
 //	  					  Ipv4Address STAaddr =  sta_nodes.Get((i*number_of_STA) +j)->GetObject<Ipv4> ()->GetAddress (1, 0).GetLocal ();
 //	  		  			  NS_LOG_ERROR((i*number_of_STA) +j<<" "<<STAaddr<<" "<<gw_ip<<" ");

	  				Ptr<Ipv4> ipv4STA = sta_nodes.Get((i*number_of_STA) +j)->GetObject<Ipv4> ();            // Static Routing
	  				Ipv4StaticRoutingHelper STA;
	  				Ptr<Ipv4StaticRouting> staticSTA = STA.GetStaticRouting (ipv4STA);
	  				staticSTA->AddNetworkRouteTo (Ipv4Address ("192.169.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
	  				staticSTA->AddNetworkRouteTo (Ipv4Address ("192.168.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
	  				//staticSTA1->AddNetworkRouteTo (Ipv4Address ("10.0.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
	  			}
	  		}

	  	 	//Static routes for AP
	  		 std::string ap_gw_ip_start = "10.0";
	  		 int ip_d = 0;
	  	     for(int i =0; i<number_of_sw;i++)
	  	     {
	  				for(int j=0;j<number_of_AP;j++)
	  			{
	  					int c;

	  					if (j == 254)
	  					{
	  						c = 1;
	  					}
	  					else
	  					{
	  				    c = (j/127);
	  					}
	  				//	NS_LOG_ERROR(c<<" "<<i*number_of_AP+j);
	  					std::string c_str = std::to_string(c);
	  					//int ip_d = ((i%250)+2);

	  					if (ip_d < 254)
	  					{
	  					ip_d = ip_d + 2;
	  					}
	  					else{
	  						ip_d = 0;
	  					    }
	  					std::string d_str =std::to_string(ip_d);
	  					std::string d = ap_gw_ip_start+"."+c_str+"."+d_str ;
	  					const char *gw_ip = d.c_str();

	  	//			     Ipv4Address Apaddr = ap_nodes.Get(i*number_of_AP+j)->GetObject<Ipv4> ()->GetAddress (1, 0).GetLocal ();
	  	//				 NS_LOG_ERROR(i*number_of_AP+j<<" "<<Apaddr<<" "<<gw_ip<<" ");

	  	 		 Ptr<Ipv4> ipv4AP1 = ap_nodes.Get(i*number_of_AP+j)->GetObject<Ipv4> ();
	  	 		// NS_LOG_ERROR(i*number_of_AP+j<<" "<<gw_ip);
	  	   	     Ipv4StaticRoutingHelper AP1;
	  	    	 Ptr<Ipv4StaticRouting> staticAP1 = AP1.GetStaticRouting (ipv4AP1);
	  	    	 staticAP1->AddNetworkRouteTo (Ipv4Address ("192.169.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
	  	    	 staticAP1->AddNetworkRouteTo (Ipv4Address ("192.168.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address (gw_ip), 1);
	  	    	// NS_LOG_ERROR(gw_ip);
	  	       }
	  		}

		  	 	//Static routes for Switches
	  		std::string nxt_hop_ip_start = "10.";
	  		std::string nxt_hop_ip_end = ".0";
	  		int nxt_hop_c = 0;
	  		std::string sw_gw_ip_start = "10.0";
	  	    ip_d = 1;
	  	    for(int i = 0; i<number_of_sw;i++)
	  	     {
	  	       for(int j=0;j<number_of_AP;j++)
	  			{
	  				int nxt_hop_b = ((i*number_of_AP+j)/250+1);
	  			    std::string nxt_hop_b_str = std::to_string(nxt_hop_b);
	  				// std::string nxt_hop_c_str = std::to_string(nxt_hop_c);
	  				 std::string nxt_hop_c_str;// = std::to_string(nxt_hop_c);


	  					 std::string d_str =std::to_string(ip_d);
	  					if (ip_d <= 253)
	  					{
	  					ip_d +=2;
	  					}
	  					else{
	  						ip_d = 1;
	  					}

	  					if (nxt_hop_c < 250)
	  								{
	  						 	 	 nxt_hop_c_str = std::to_string(nxt_hop_c);
	  								 nxt_hop_c +=1;
	  								}
	  								else{

	  									 nxt_hop_c = 0;
	  									 nxt_hop_c_str = std::to_string(nxt_hop_c);
	  									 nxt_hop_c +=1;
	  								}
	  					std::string nxt_hop_sw = nxt_hop_ip_start+nxt_hop_b_str+"."+ nxt_hop_c_str+nxt_hop_ip_end;
	  					const char *nxt_hop =nxt_hop_sw.c_str();

	  					int gw_ip_c = ((i*number_of_AP+j)/128);
	  					std::string gw_ip_c_str = std::to_string(gw_ip_c);
	  					std::string gw_ip_nw= sw_gw_ip_start+"."+gw_ip_c_str+"."+d_str ;
	  					const char *gw_ip = gw_ip_nw.c_str();


	  	////
	  	//				Ipv4Address SWaddr1 = sw_nodes.Get(i)->GetObject<Ipv4> ()->GetAddress (j+1, 0).GetLocal ();
	  	//			   NS_LOG_ERROR(j<<" "<<SWaddr1<<" "<<gw_ip<<" "<<nxt_hop<<" ");

	  	     Ptr<Ipv4> ipv4SW1 = sw_nodes.Get(i)->GetObject<Ipv4> ();            // Static Routing
	  	     Ipv4StaticRoutingHelper SW1;
	  	     Ptr<Ipv4StaticRouting> staticSW1 = SW1.GetStaticRouting (ipv4SW1);
	  	     staticSW1->AddNetworkRouteTo (Ipv4Address (nxt_hop),Ipv4Mask("255.255.255.0"), Ipv4Address (gw_ip),j+1);
	  		//  staticSW1->AddNetworkRouteTo (Ipv4Address ("10.1.1.0"),Ipv4Mask("255.255.255.0"), Ipv4Address ("10.0.0.3"), 2);




	        	}
	  	        Ptr<Ipv4> ipv4SW1 = sw_nodes.Get(i)->GetObject<Ipv4> ();            // Static Routing
	  	        Ipv4StaticRoutingHelper SW1;
	  	       Ptr<Ipv4StaticRouting> staticSW1 = SW1.GetStaticRouting (ipv4SW1);

	  	  	   Ipv4Address CTLaddr = ctl->GetObject<Ipv4> ()->GetAddress (i+1, 0).GetLocal ();
	  	       staticSW1->AddNetworkRouteTo (Ipv4Address ("192.169.0.0"),Ipv4Mask("255.255.0.0"), CTLaddr,(number_of_AP+1));
	  	 	   //NS_LOG_ERROR(number_of_AP+1<<" "<<CTLaddr);
	  		 }


 //	  	     int gw_ip_end =1;
	  		 nxt_hop_c = 0;
 //	  		 std::string GW_gw_ip_start = "192.169.";

	  	 	for(int i = 0; i<number_of_sw;i++)
	  	     {
	  	       for(int j=0;j<number_of_AP;j++)
	  			{
	  				int nxt_hop_b = ((i*number_of_AP+j)/250+1);
	  			    std::string nxt_hop_b_str = std::to_string(nxt_hop_b);
	  				// std::string nxt_hop_c_str = std::to_string(nxt_hop_c);
	  			    std::string nxt_hop_c_str;// = std::to_string(nxt_hop_c);

	  				if (nxt_hop_c < 250)
	  								{
	  						 	 	 nxt_hop_c_str = std::to_string(nxt_hop_c);
	  								 nxt_hop_c +=1;
	  								}
	  								else{
	  									 nxt_hop_c = 0;
	  									 nxt_hop_c_str = std::to_string(nxt_hop_c);
	  									 nxt_hop_c +=1;
	  								}


	  					std::string nxt_hop_nw_ip = nxt_hop_ip_start+nxt_hop_b_str+"."+ nxt_hop_c_str+nxt_hop_ip_end;
	  					const char *nxt_hop =nxt_hop_nw_ip.c_str();

    //	  					int gw_ip_c = (i/128);
    //	  							std::string gw_ip_c_str = std::to_string(gw_ip_c);
    //
    //	  							std::string gw_ip_d_str;
    //	  					     	if (gw_ip_end > 255)
    //	  							  	   {
 //	  									gw_ip_end = 1;
 //	  									std::to_string(gw_ip_end);
 //	  							  	   }
 //	  							gw_ip_d_str =std::to_string(gw_ip_end);
 //	  							std::string d= GW_gw_ip_start+gw_ip_c_str+"."+gw_ip_d_str ;
 //	  							const char *gw_ip = d.c_str();
     	//
	  	//				Ipv4Address GWaddr = gw->GetObject<Ipv4> ()->GetAddress (i+1, 0).GetLocal ();
	  	//			    NS_LOG_ERROR(i+1<<" Interface "<<GWaddr<<" GW "<<gw_ip<<" ,Ntx Hop "<<nxt_hop);



	  		 Ptr<Ipv4> ipv4GW1 = gw->GetObject<Ipv4> ();            // Static Routing
	  	     Ipv4StaticRoutingHelper GW1;
	  	     Ptr<Ipv4StaticRouting> staticGW1 = GW1.GetStaticRouting (ipv4GW1);
	  		 staticGW1->AddNetworkRouteTo (Ipv4Address (nxt_hop),Ipv4Mask("255.255.255.0"), Ipv4Address ("192.169.0.1"),1);
	  		 staticGW1->AddNetworkRouteTo (Ipv4Address ("10.0.0.0"),Ipv4Mask("255.255.0.0"), Ipv4Address ("192.169.0.1"),1);

	  		//nxt_hop = 10.1.j.0

	  			}
	  			}


	  	 	int gw_ip_end=1;
	  	     nxt_hop_c = 0;
	  	     std::string CTL_gw_ip_start = "192.168.";

	  	 	for(int i = 0; i<number_of_sw;i++)
	  	     {
	  	       for(int j=0;j<number_of_AP;j++)
	  			{
	  	    	    int nxt_hop_b = ((i*number_of_AP+j)/250+1);
	  			    std::string nxt_hop_b_str = std::to_string(nxt_hop_b);
	  			    std::string nxt_hop_c_str;// = std::to_string(nxt_hop_c);
	  				  if (nxt_hop_c < 250)
	  							{
	  								 nxt_hop_c_str = std::to_string(nxt_hop_c);
	  								 nxt_hop_c +=1;
	  							}
	  					else    {
	  								 nxt_hop_c = 0;
	  								 nxt_hop_c_str = std::to_string(nxt_hop_c);
	  								 nxt_hop_c +=1;
	  							}
	  					std::string nxt_hop_ip = nxt_hop_ip_start+nxt_hop_b_str+"."+ nxt_hop_c_str+nxt_hop_ip_end;
	  					const char *nxt_hop =nxt_hop_ip.c_str();

	  					int gw_ip_c = (i/128);
	  					std::string gw_ip_c_str = std::to_string(gw_ip_c);

	  					std::string gw_ip_d_str;
	  			     	if (gw_ip_end > 255)
	  					  	   {
	  							gw_ip_end = 1;
	  							std::to_string(gw_ip_end);
	  					  	   }
	  					gw_ip_d_str =std::to_string(gw_ip_end);
	  					std::string d= CTL_gw_ip_start+gw_ip_c_str+"."+gw_ip_d_str ;
	  					const char *gw_ip = d.c_str();

	  	//				Ipv4Address CTLaddr = ctl->GetObject<Ipv4> ()->GetAddress (i+1, 0).GetLocal ();
	  	//			    NS_LOG_ERROR(i+1<<" Interface "<<CTLaddr<<" GW "<<gw_ip<<" ,Ntx Hop "<<nxt_hop);

	  		 Ptr<Ipv4> ipv4CTL = ctl->GetObject<Ipv4> ();            // Static Routing
	  	     Ipv4StaticRoutingHelper CTL;
	  	     Ptr<Ipv4StaticRouting> staticCTL = CTL.GetStaticRouting (ipv4CTL);
	  		 staticCTL->AddNetworkRouteTo (Ipv4Address (nxt_hop),Ipv4Mask("255.255.255.0"), Ipv4Address (gw_ip), i+1);
	  		 //nxt_hop = 10.1.j.0
	  			}
	  	       gw_ip_end +=2;
	  			}
//**********************************************************************************************

	// NS_LOG_INFO ("Create V4Ping Appliation");
	Ptr<V4Ping> app = CreateObject<V4Ping> ();
	app->SetAttribute ("Remote", Ipv4AddressValue ("192.169.0.2"));
	app->SetAttribute ("Verbose", BooleanValue (true));
	sta_nodes.Get(0)->AddApplication (app);
	app->SetStartTime (Seconds (3.0));
    app->SetStopTime (Seconds (21.0));
	 
		Simulator::Run ();	
  return 0;
}