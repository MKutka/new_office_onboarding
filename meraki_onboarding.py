import cities
import infoblox
import ipaddress
import ise_api
import json
import meraki
import meraki_api
import requests
import time
from ise import ERS
from infoblox_client import connector
from infoblox_client import objects
from infoblox_client.object_manager import InfobloxObjectManager
from progress.bar import IncrementalBar
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Time Zones
AST = 'America/Anchorage'
EST = 'America/New_York'
CST = 'America/Chicago'
MST = 'America/Denver'
PST = 'America/Los_Angeles'

# Maps states to their timezones
timezone_dict = {"AK": AST,"AL": CST, "AZ": MST, "AR": CST, "CA": PST, "CO": MST, "CT": EST,
                 "DE": EST, "DC": EST, "FL": EST, "GA": EST, "ID": MST, "IL": CST, "IN": EST, "IA": CST,
                 "KS": CST, "KY": CST, "LA": CST, "ME": EST, "MD": EST, "MA": EST, "MI": EST, "MN": CST,
                 "MS": CST, "MO": CST, "MT": MST, "NE": CST, "NV": PST, "NH": EST, "NJ": EST, "NM": MST,
                 "NY": EST, "NC": EST, "ND": CST, "OH": EST, "OK": CST, "OR": PST, "PA": EST,
                 "RI": EST, "SC": EST, "SD": CST, "TN": CST, "TX": CST, "UT": MST, "VT": EST, "VA": EST,
                 "WA": PST, "WV": EST, "WI": CST, "WY": MST}

# Logging into Infoblox to assign network
url = infoblox.url + "member"
client = requests.Session()
cookies = client.get(url, verify=False)
login_data = dict(username=infoblox.user, password=infoblox.pwd, csrfmiddlewaretoken=cookies, next='/')
r = client.post(url, data=login_data, headers=dict(Referer=url))

## Create Site variables for Infoblox name
#Enter 2 Letter state code
while True:
    state = input("""Enter 2 letter State Code:  """)
    state = state.upper()
    if str(state) not in timezone_dict.keys():
        print("Invalid Syntax!")
        continue
    if len(state) == 2:
        break
    else:
        print("Invalid Syntax!")
        continue

# Enter City Name
while True:
    city = input("""Enter City Name:  """)
    city = city.title()
    if str(city) not in cities.cities_list():
        print("Invalid Syntax! - Confirm Correct Spelling!")
        continue
    else:
        break

# Enter Remote Site Mailing address
address = input("Enter remote-site mailing address: ")
address.title()
name = "US-" + city + "-" + state

## Does the site use static or Dynamic IP Addresses
while True:
    check_ip = input("Does the site have static IP Addresses? y/n: ")
    if 'y' in check_ip:
        def create_ip_gateway():
            try:
                public_address_gateway = input("Enter External (ISP) IP Gateway Address: _._._._: ")
                return str(ipaddress.ip_address(public_address_gateway))
            except ValueError:
                print("Invalid IP, please try again.")
                create_ip_gateway()
        
        public_address_gateway = create_ip_gateway()
        print(f"You entered: {public_address_gateway}")

        public_address = input("Enter External IP and Prefix (_._._._/_) to be added to MX: ")
        check = '/' in public_address
        if check:
            break
        else:
            print("Invalid Syntax!")
            continue
    else:
        break

def create_dns():
    try:
        dns_server = input("Enter DNS server: _._._._: ")
        return str(ipaddress.ip_address(dns_server))
    except ValueError:
        print("Invalid IP, please try again.")
        create_dns()

dns_server = create_dns()
    
# Create Infoblox IPAM Supernet Network
url = infoblox.url + "network?_return_fields%2B=network"
supernet_network = input("Enter Supernet Prefix _._._._/_: ")
comment = name
payload = json.dumps({"network": supernet_network, "comment": comment})
requests.request("POST", url, headers=infoblox.ib_auth_headers, data=payload, verify=False)
clean_ip_address_list = supernet_network.replace(' ', '').split('.')
site_id = clean_ip_address_list[1]
print("Creating Infoblox IPAM and DHCP Scopes...")

# Create Infoblox IPAM Sub-Networks W/ DHCP
opts = {'host': infoblox.host, 'username': infoblox.user, 'password': infoblox.pwd}
conn = connector.Connector(opts)
object_mgr = InfobloxObjectManager(conn)

vlan101 = '10.' + site_id + '.32.0/20'
vlan103 = '10.' + site_id + '.3.0/24'
vlan104 = '10.' + site_id + '.8.0/24'
vlan105 = '10.' + site_id + '.5.0/24'
vlan106 = '10.' + site_id + '.6.0/24'
vlan110 = '10.' + site_id + '.16.0/20'
vlan111 = '10.' + site_id + '.12.0/22'
vlan130 = '10.' + site_id + '.130.0/24'
vlan131 = '10.' + site_id + '.131.0/24'
vlan148 = '10.' + site_id + '.48.0/20'

def add_ib_subnets(ib_subnet, ib_gateway_ip):
    ib_subnets = InfobloxObjectManager(conn)
    return ib_subnets.create_network(net_view_name='default',
                                     cidr=ib_subnet,
                                     nameservers=['172.18.104.224', '172.18.104.225'],
                                     members=infoblox.ms_servers,
                                     gateway_ip=ib_gateway_ip)

ib_subnet_list = [vlan101, vlan103, vlan104, vlan105, vlan106, vlan110, vlan111, vlan130,
                  vlan131, vlan148]
comment_dict = {vlan101: name + " - " 'Wired Data',
                vlan103: name + " - " 'Server',
                vlan104: name + " - " 'Wired Guest',
                vlan105: name + " - " 'Management',
                vlan106: name + " - " 'Security_Network',
                vlan110: name + " - " 'VoIP',
                vlan111: name + " - " 'ig-employee',
                vlan130: name + " - " 'ig-guest',
                vlan131: name + " - " 'Solstice',
                vlan148: name + " - " 'ig-corp'}
bar = IncrementalBar('Provisioning...', max=len(ib_subnet_list))
for ib_subnet in ib_subnet_list:
    bar.next()
    time.sleep(1)
    clean_ip_address_list = ib_subnet.replace(' ', '').split('.')
    clean_ip_address_list[3] = '1'
    ib_gateway_ip = '.'.join(clean_ip_address_list)
    ib_subnet_response = add_ib_subnets(ib_subnet, ib_gateway_ip)

    # Add Comments to Infoblox Subnets
    comment_url = infoblox.url + ib_subnet_response._ref
    comment_payload = {"network": ib_subnet,
                       "comment": comment_dict[ib_subnet]
                       }
    ib_comment_response = requests.request("PUT", comment_url, 
                                           headers=infoblox.ib_auth_headers, 
                                           data=comment_payload, 
                                           verify=False)
    
     # Add DHCP ranges to subnets
    dhcp_clean_ip_address_list = ib_subnet.replace(' ', '').split('.')
    dhcp_clean_ip_address_list.pop(3)
    dhcp_clean_ip_address_list.append('')
    dhcp_ib_range_prefix = '.'.join(dhcp_clean_ip_address_list)
    ranges_url = infoblox.url + "range"
    dhcp_range_payload = json.dumps({"start_addr": dhcp_ib_range_prefix + '100',
                                     "end_addr": dhcp_ib_range_prefix + '245',
                                     # "server_association_type": "MS_FAILOVER",
                                     "server_association_type": "MS_SERVER",
                                     # "failover_association": ""dcedhcp02.insightglobal.net-dcwdhcp02.insightglobal.net"",
                                     "network_view": "default",
                                     "name": comment_dict[ib_subnet],
                                     "ms_server": {"_struct": "msdhcpserver",
                                                   "ipv4addr": "dcedhcp02.insightglobal.net"
                                                  },
                                     "ms_options":
                                         [{"name": "routers",
                                           "num": 3,
                                           "value": ib_gateway_ip}]
                                     })
    ib_dhcp_response = requests.request("POST", ranges_url, headers=infoblox.ib_auth_headers, data=dhcp_range_payload,
                                        verify=False)
    bar.finish()

print("Infoblox IPAM, DHCP Scopes and MAC Reservations Created succesfully...")

# Creating new Meraki Network
print('Creating Meraki Network... ' + name)
product_types = ['appliance', 'switch', 'camera', 'Wireless']
tz = timezone_dict.get(state)
dashboard = meraki.DashboardAPI(meraki_api.api_key, suppress_logging=True, print_console=False)
response = dashboard.organizations.createOrganizationNetwork(meraki_api.org_id, total_pages='all', name=name,
                                                             productTypes=product_types, timeZone=tz, notes=None)

# Add hardware and licensing to newly created networks
claimed = input('Has the hardware and required licensing already been added to the Meraki Dashboard?: y/n ')
if claimed == 'n':
    order = input("Enter Meraki Order Number: ")
    if order == '':
        pass
    else:
        order_lookup_response = dashboard.organizations.claimIntoOrganization(meraki_api.org_id, orders=order).json()
        serials = [x['serial'] for x in response if x['orderNumber'] == order]
        networks_url = "https://api.meraki.com/api/v1/organizations/" + meraki_api.org_id + "/networks"
        order_response = requests.request("GET", networks_url, headers=meraki_api.headers).json()
        for x in order_response:
            print(x)
            if str(x['name']) == name:
                id = str(x['id'])
                continue_network = 'y'
                if continue_network == 'y':
                    device_list = serials
                    device_Serial_prefix = {
                        'Q2DD': {
                            'type': '-AP-',
                            'count': 1
                        },
                        'Q3AC': {
                            'type': '-AP-',
                            'count': 1
                        },
                        'Q2WN': {
                            'type': '-MX-',
                            'count': 1
                        },
                        'Q2YN': {
                            'type': '-MX-',
                            'count': 1
                        },
                        'Q2JN': {
                            'type': '-MX-',
                            'count': 1
                        },
                        'Q2WP': {
                            'type': '-SW-',
                            'count': 1
                        },
                        'Q2UX': {
                            'type': '-SW-',
                            'count': 1
                        },
                    }
                    add_devices_response = dashboard.networks.claimNetworkDevices(id, device_list).json()

                    for y in device_list:
                        device_name = city + device_Serial_prefix[y[0:4]]['type'] + str(
                            device_Serial_prefix[y[0:4]]['count'])
                        device_Serial_prefix[y[0:4]]['count'] += 1
                        name_device_response = dashboard.devices.updateDevice(y, name=device_name,
                                                                              address=address).json()
                        print("Devices Added to Meraki Network Successfully...")

# Add New Site Location to ISE
ise_location_name = name.replace("-", " ")
ise_site_url = f"https://{ise_api.url}:9060/ers/config/networkdevicegroup"
ise_payload = {"NetworkDeviceGroup": {
                        "name": "Location#All Locations#" + ise_location_name,
                        "othername": "Location",
                        "description": name,
                        "link": {
                            "rel": "self",
                            "href": f"https://{ise_api.url}/ers/config/networkdevicegroup",
                            "type": "application/json"
                        }
                    },
                }
ise_location_response = requests.request("POST", ise_site_url, headers=ise_api, json=ise_payload, verify=False)

# Add Devices to ISE
clean_ip_address_list = vlan105.replace(' ', '').split('.')
switch_applianceIp = '.'.join(clean_ip_address_list)
site_prefix = switch_applianceIp.replace('0/24', '')

def add_device(ise_device_name, device_type, device_ip):
    ise = ERS(ise_node=ise_api.url, ers_user=ise_api.user, ers_pass=ise_api.password, verify=False, disable_warnings=True)
    return ise.add_device(name=ise_device_name, 
                          ip_address=device_ip, 
                          radius_key=ise_api.radius_key, 
                          snmp_ro=ise_api.snmp_string, 
                          dev_location='Location#All Locations#' + ise_location_name,
                          dev_type=device_type)