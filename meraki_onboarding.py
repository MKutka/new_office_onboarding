import cities
import infoblox
import ipaddress
import requests



# Time Zones
EST = 'America/New_York'
CST = 'America/Chicago'
MST = 'America/Denver'
PST = 'America/Los_Angeles'

# Maps states to their timezones
timezone_dict = {"AL": CST, "AZ": MST, "AR": CST, "CA": PST, "CO": MST, "CT": EST,
                 "DE": EST, "DC": EST, "FL": EST, "GA": EST, "ID": MST, "IL": CST, "IN": EST, "IA": CST,
                 "KS": CST, "KY": CST, "LA": CST, "ME": EST, "MD": EST, "MA": EST, "MI": EST, "MN": CST,
                 "MS": CST, "MO": CST, "MT": MST, "NE": CST, "NV": PST, "NH": EST, "NJ": EST, "NM": MST,
                 "NY": EST, "NC": EST, "ND": CST, "OH": EST, "OK": CST, "OR": PST, "PA": EST,
                 "RI": EST, "SC": EST, "SD": CST, "TN": CST, "TX": CST, "UT": MST, "VT": EST, "VA": EST,
                 "WA": PST, "WV": EST, "WI": CST, "WY": MST}

# Logging into Infoblox to assign network
client = requests.Session()
cookies = client.get(infoblox.url, verify=False)
login_data = dict(username=infoblox.user, password=infoblox.pwd, csrfmiddlewaretoken=cookies, next='/')
r = client.post(infoblox.url, data=login_data, headers=dict(Referer=infoblox.url))

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
# while True:
#     check_ip = input("Does the site have static IP Addresses? y/n: ")
#     if 'y' in check_ip:
