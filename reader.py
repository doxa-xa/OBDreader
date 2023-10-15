import sys
import time
import serial
from error_codes_prefix import trouble_code_prefix
from ISO_OBD_error_codes import trouble_code_descriptions

SERIAL_PORT_NAME = '/dev/serial/by-id/'
SERIAL_PORT_BAUD = 115200 #38400
SERIAL_PORT_TIMEOUT = 60 

ELM_CONNECT_SETTLE_PERIOD = 5
ELN_CONNECT_TRY_COUNT = 5

def get_response(serial_con, data):
    serial_con.write(data)
    response = ''
    read_char = 1
    while read_char != b'>' and read_char !=0: # '>' character is the end of the prompt
        read_char = serial_con.read()
        if read_char != b'>':
            response += str(read_char, 'utf=8')
    return response.replace('\r','\n').replace('\n\n','\n') #removes blank spaces and blank lines

def prune_data(data, remove_byte_count):
    response = ''
    lines = data.split('\n')
    for line in lines:
        response += line[2 * remove_byte_count:]
    return response

def data_to_trouble_codes(data):
    trouble_codes = list()
    while len(data) >0:
        code = data[:4]
        if int(code) != 0:
            trouble_codes.append(trouble_code_prefix[code[0]]+ code[1:])
        data = data[4:]
    return trouble_codes

def get_trouble_code_data(ELM327, OBDIImode):
    trouble_code_data = ''
    response = get_response(ELM327, OBDIImode +b'\r')
    response = prune_data(response, 1)
    trouble_codes = data_to_trouble_codes(response)
    for trouble_code in trouble_codes:
        trouble_code_data += trouble_code
        try:
            trouble_code_data += " : " + trouble_code_descriptions[trouble_code] + '\n'
        except:
            trouble_code_data += " : [DESCRIPTION NOT FOUND] \n"
    return trouble_code_data

ELM327 = serial.Serial(port=SERIAL_PORT_NAME, baudrate=SERIAL_PORT_BAUD)
ELM327.timeout = SERIAL_PORT_TIMEOUT
ELM327.write_timeout = SERIAL_PORT_TIMEOUT
print(f'Serial Port: {ELM327.name}')

#initialize the ELM327
response = get_response(ELM327, b'AT Z\r')
print(response)

#Echo off, for faster communication
response = get_response(ELM327, b'AT E0\r')
if response != 'AT E0\nOK\n':
    print('FAILED:AT E0 - set echo off')
else:
    print('SUCCESS:AT E0 - set echo off')


#don't print white spaces for faster communication
response = get_response(ELM327, b'AT S0\r')
if response != 'OK\n':
    print('FAILED:AT S0 - set white spaces off')
else:
    print('SUCCESS:AT S0 - set white spaces off')

#set CAN communication protocol to ISO 9141-2
response = get_response(ELM327, b'AT SP A3\r')
if response != 'OK\n':
    print('FAILED: AT SP A3 - set protocol to ISO 9141-2')
else:
    print('SUCCESS: AT SP A3 - set protocol to ISO 9141-2')

#set CAN Baud to high speed
response = get_response(ELM327, b'AT IB 10\r')
if response != 'OK\n':
    print('FAILED: AT IB 10 - set high speed CAN BUS')
else:
    print('SUCCESS: AT IB 10 - set high speed CAN BUS')

#get ELM description
response = get_response(ELM327, b'AT @1\r')
print(f'ELM Device Description:{response}')

response = get_response(ELM327, b'AT @2\r')
print(f'ELM Device User Description:{response}')

#get Voltage at the connector
response = get_response(ELM327, b'AT RV\r')
print(f'Volt reading at OBDII Connector:{response}')

#initial connection to OBDII CAN BUS
print('CONNECTING TO CAN BUS FOR OBDII COMMUNICATION...')
num_tries = 5
response = 'UNABLE TO CONNECT'
while response.find('UNABLE TO CONNECT') != -1 and num_tries > 0:
    num_tries -= 1
    #waiting for ELM connection settle 
    count = ELM_CONNECT_SETTLE_PERIOD
    while count > 0:
        sys.stdout.write('\r'+str(count))
        sys.stdout.flush()
        time.sleep(1)
        count -= 1
    sys.stdout.write('\r\r')
    sys.stdout.flush()
    #request Mode 1 PID 0 to test connection
    response = get_response(ELM327, b'0100\r')
    if response.find('UNABLE TO CONNECT') != -1:
        print(f'TRYING TO RECONNECT... ({str(num_tries)})')

if response.find('UNABLE TO CONNECT') != -1:
    print('FAILED TO CONNECT TO CAN BUS')
    #closing the serial port 
    ELM327.close()
    quit()

#get the current OBDII data protocol
response = get_response(ELM327, b'AT DP\r')
print(f'USING CAM BUS Protocol: {response}')

#get vehile VIN number
response = get_response(ELM327, b'0902\r')
response = prune_data(response, 3)
response = str(bytearray.fromhex(response).replace(bytes([0x00]),b' '), 'UTF-8')
print(f'Vehicle VIN: {str(response)} \n')

#get stored errors from ECU
response = get_trouble_code_data(ELM327, b'03')
print('Stored errors:')
print(response)

#get pending errors from ECU
response = get_trouble_code_data(ELM327, b'07')
print('Pending errors:')
print(response)

#Close Serial port
ELM327.close()

