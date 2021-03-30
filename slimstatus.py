#!/usr/bin/env python3

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime
import os
from threading import Thread
import requests
import socket


### jinja setup
env = Environment(
    loader=FileSystemLoader('./'),
    autoescape=select_autoescape(['html', 'xml'])
)
template = env.get_template('page.jinja')



### load config
with open('config.yml') as f:
	data = yaml.safe_load(f)




###TESTS
def test_ping(target,ipv,_):
	result = os.system(f"ping -{ipv} -c 1 {target} > /dev/null")
	return {
		0: True,
		1: "Ping failed",
		256: "Host unreachable",
		512: "Name not resolved"
	}[result]
		
	
	
def test_https(target,ipv,port):
	r = requests.get("https://" + target)
	result = r.status_code
	return {
		200: True,
		403: "Authentication Failure",
		404: "Not found"
	}[result]


def test_port(target,ipv,port):
	af = socket.AF_INET6 if ipv==6 else socket.AF_INET
	with socket.socket(af, socket.SOCK_STREAM) as sock:
		result = sock.connect_ex((target,port))
	return {
		0: True,
		101: "Unknown Name",
		111: "Wat"
	}[result]

tests = {
	"port":test_port,
	"https":test_https
}

### threaded op to perform and write results
def perform_test(test,info,ipv,testarg=None):
	target = info.get("target")
	if f"target_{ipv}" in info: target = info.get(f"target_{ipv}")
	try:
		result = test(target,ipv,testarg)
	except:
		result = "Unknown Error"
	if result is not True:
		info['errors'].append(f"IPv{ipv}: {result}")
		info[f'operational_{ipv}'] = False



threads = []

### perform all tests
for service in data['services']:
	#service['operational'] = True
	service['errors'] = []
	
	
	for ipv in [4,6]:
		service[f'operational_{ipv}'] = None
		if "target" in service or f"target_{ipv}" in service:
			service[f'operational_{ipv}'] = True
			for testtype,value in service['tests'].items():
				test = tests[testtype]
				t = Thread(target=perform_test,args=(test,service,ipv),kwargs={'testarg':value})
				threads.append(t)
				t.start()
	
	
for machine in data['machines']:
	#machine['operational'] = True
	machine['errors'] = []

	for ipv in [4,6]:
		machine[f'operational_{ipv}'] = None
		if "target" in machine or f"target_{ipv}" in machine:
			machine[f'operational_{ipv}'] = True
			for test in [test_ping]:
				t = Thread(target=perform_test,args=(test,machine,ipv),kwargs={})
				threads.append(t)
				t.start()


### wait until done	
for t in threads:
	t.join()



for r in data['services'] + data['machines']:
	r['operational'] = (r['operational_4'] in (True,None) and r['operational_6'] in (True,None))



### extra information
data['meta'] = {'date':datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")}




### write result
with open("page.html","w") as output:
	output.write(template.render(data))

