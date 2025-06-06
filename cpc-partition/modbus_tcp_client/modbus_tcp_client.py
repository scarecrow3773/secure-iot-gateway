import asyncio
import xml.etree.ElementTree as ET
from pyModbusTCP.client import ModbusClient
from pyModbusTCP.utils import test_bit, set_bit
from multiprocessing import shared_memory
import json
import xmlschema
import logging
import os
import time
import posix_ipc

_logger = logging.getLogger(__name__)

class ModbusTCPClient:
    def __init__(self, ipaddr: str, port: int, serveralias: str, endpoints: dict[str, dict[str, str | int | bool]]):
        self.ipaddr = ipaddr
        self.endpoints = endpoints
        self.serveralias = serveralias
        self.client = ModbusClient(host=ipaddr, port=port, unit_id=1, auto_open=True)
        self.client.timeout = 1.0
        self.status = self.client.is_open
        self._last_connection_attempt_time = 0
        self._retry_interval = 5
    
    def retry_connection(self) -> None:
        """
        Retry to connect to the ModbusTCP server.
        """
        current_time = time.time()
        if current_time - self._last_connection_attempt_time < self._retry_interval:
            return  # Do not attempt to reconnect if the retry interval has not passed
        self._last_connection_attempt_time = current_time # Update the last connection attempt time

        connected = self.client.open()
        if connected:
            self.status = True
            _logger.info(f"(Re)connection to {self.client.host} successful.")  
        else:
            self.status = False
            _logger.error(f"Reconnection to {self.client.host} failed.")  

    def fc01_read_coil_status(self, name: str) -> bool | None:
        """
        Read coil status from the ModbusTCP server.
        name: The name of the endpoint to read.
        return: The value of the coil.
        """
        endpoint = self.endpoints[name]
        address = endpoint['address']
        quantity = endpoint['quantity']
        request = self.client.read_coils(address, quantity)
        return request[0]

    def fc02_read_discrete_inputs(self, name: str) -> bool | None:
        """
        Read discrete inputs from the ModbusTCP server.
        name: The name of the endpoint to read.
        return: The value of the discrete input.
        """
        endpoint = self.endpoints[name]
        address = endpoint['address']
        quantity = endpoint['quantity']
        request = self.client.read_discrete_inputs(address, quantity)
        return request[0]

    def fc03_read_holding_registers(self, name: str) -> tuple[int | bool | None, str | None]:
        """
        Read holding registers from the ModbusTCP server.
        name: The name of the endpoint to read.
        return: A tuple with the value and the datatype of the value.
        """
        endpoint = self.endpoints[name]
        address = endpoint['address']
        quantity = endpoint['quantity']
        bit_offset = endpoint['offset']

        # Create a read registers request
        request = self.client.read_holding_registers(address, quantity)
        if request is not None and bit_offset > -1:
            value = test_bit(request[0], bit_offset)
            datatype = "Boolean"# if bit_offset > -1 else "ByteString"
            return value, datatype
        elif request is not None and bit_offset == -1:
            return request[0], "UInt16"
        else:
            return None, None

    # def write_coils(self, name, value):
    #     endpoint = self.endpoints[name]
    #     address = endpoint['address']

    #     # Create a write coils request
    #     response = self.client.write_single_coil(address, value)
    #     return response

    # def write_registers(self, name, value):
    #     endpoint = self.endpoints[name]
    #     address = endpoint['address']

    #     # Create a write registers request
    #     response = self.client.write_multiple_registers(address, value)
    #     return response


class ModbusClientManager:
    def __init__(self, xml_config_path: str, xsd_path: str):
        self.xml_config_path = xml_config_path
        self.xsd_path = xsd_path
        self.endpoints = self.load_endpoints_from_xml()
        self.clients = self.create_clients()

    def create_clients(self) -> list[ModbusTCPClient]:
        """
        Create ModbusTCP clients for each server in the endpoints dictionary.
        return: A list of ModbusTCP clients.
        """
        modbus_clients = []
        if self.endpoints is None:
            return []
        else:
            for ipaddr, port, serveralias in self.endpoints:
                client_endpoints = self.endpoints[(ipaddr, port, serveralias)]
                modbus_client = ModbusTCPClient(ipaddr, port, serveralias, client_endpoints)
                modbus_clients.append(modbus_client)
        return modbus_clients

    async def start_clients(self) -> None:
        """
        Connect to the ModbusTCP servers.
        """
        #await asyncio.gather(*(client.connect() for client in self.clients))
        pass

    async def stop_clients(self) -> None:
        """
        Close the ModbusTCP connections.
        """
        client: ModbusTCPClient
        for client in self.clients:
            client.client.close()
    
    async def periodic_read(self, interval: float, shm_list: list[shared_memory.SharedMemory], semaphore_list: list[posix_ipc.Semaphore]) -> None:
        """
        Periodically read the ModbusTCP values and write them to shared memory.
        interval: The time interval in seconds between each read operation.
        shm_list: A list of shared memory objects to write the ModbusTCP values to.
        semaphore_list: A list of semaphores to control access to the shared memory objects.
        """
        # Abort if no Modbus clients have been created
        if self.clients == []:
            _logger.error(f"Modbus client list is empty. Periodic value reading aborted.")
            return

        while True:
            modbus_values = {}
            client: ModbusTCPClient
            for client in self.clients:
                if not client.client.is_open:
                    client.retry_connection()
                if not client.client.is_open: # Check again if the connection was successful
                    modbus_values[f"ModbusTCP Connections:{client.serveralias}: Connection status"] = {
                                                    "value": False,
                                                    "varType": "Boolean",
                                                    "description": "Connection status to the Modbus server"
                                                }
                if client.client.is_open:
                    modbus_values[f"ModbusTCP Connections:{client.serveralias}: Connection status"] = {
                                                    "value": True,
                                                    "varType": "Boolean",
                                                    "description": "Connection status to the Modbus server"
                                                }
                    for endpoint_name in client.endpoints:      
                        # TODO: Test with different endpoints and Modbus-Functions, e.g., Write Coils, Write Single Register, Write Multiple Registers
                        try:
                            if client.endpoints[endpoint_name]['function'] == 'Read Holding Registers':
                                register_values, datatype = client.fc03_read_holding_registers(endpoint_name)
                                if register_values is not None and datatype is not None:
                                    modbus_values[f"{client.serveralias}: {endpoint_name}"] = {
                                                            "value": register_values,
                                                            "varType": datatype,
                                                            "description": f"{client.endpoints[endpoint_name]['description']}"
                                                        }
                            elif client.endpoints[endpoint_name]['function'] == 'Read Discrete Input':   
                                discrete_input_values = client.fc02_read_discrete_inputs(endpoint_name)
                                if discrete_input_values is not None:
                                    modbus_values[f"{client.serveralias}: {endpoint_name}"] = {
                                                            "value": discrete_input_values,
                                                            "varType": "Boolean",
                                                            "description": f"{client.endpoints[endpoint_name]['description']}"
                                                        }
                            elif client.endpoints[endpoint_name]['function'] == 'Read Coil Status' or client.endpoints[endpoint_name]['function'] == 'Read Coils':
                                coil_status_values = client.fc01_read_coil_status(endpoint_name)
                                if coil_status_values is not None:
                                    modbus_values[f"{client.serveralias}: {endpoint_name}"] = {
                                                            "value": coil_status_values,
                                                            "varType": "Boolean",
                                                            "description": f"{client.endpoints[endpoint_name]['description']}"
                                                        }
                        except Exception as e:
                            _logger.error(f"Error reading {endpoint_name} from {client.ipaddr} with alias {client.serveralias}: {e}")
                            modbus_values[f"{client.serveralias}: {endpoint_name}"] = {
                                                        "value": "ERROR READING VALUE",
                                                        "varType": "String",
                                                        "description": f"{client.endpoints[endpoint_name]['description']}"
                                                    }
                            
            # Write the modbus_values to shared memory with semaphore
            for shm, sem in zip(shm_list, semaphore_list):
                sem: posix_ipc.Semaphore
                shm: shared_memory.SharedMemory

                sem.release()
                await asyncio.sleep(0.01)
                sem.acquire()
                shm_size = shm.size
                modbus_values_json = json.dumps(modbus_values)
                shm.buf[:shm_size] = b'\x00' * shm_size  # Clear the shared memory buffer
                shm.buf[:len(modbus_values_json)] = modbus_values_json.encode('utf-8')

                if len(modbus_values_json)/shm_size >= 0.9: # Log a warning if the shared memory is more than 90% full
                    _logger.error(f"ModbusTCP Shared Memory     {len(modbus_values_json)}/{shm_size} bytes used (more than 90% full).")
                sem.release()
            await asyncio.sleep(interval)

    def load_endpoints_from_xml(self) -> dict[tuple[str, int, str], dict[str, dict[str, str | int]]]:
        """
        Load the ModbusTCP endpoints from an XML file and return a dictionary with the server's IP address, port, and alias as the key.
        The value is a dictionary with the endpoint name as the key and the endpoint details as the value.
        """
        # Validate the XML file against the XSD file
        schema = xmlschema.XMLSchema(self.xsd_path)
        if not schema.is_valid(self.xml_config_path):
            _logger.error("The XML file does not conform to the provided XSD schema.")

        # Load the XML file
        try:
            tree = ET.parse(self.xml_config_path)
            print(f"Size of ModbusTCP XML file:    {os.path.getsize(self.xml_config_path)}")
        except(ET.ParseError, FileNotFoundError) as e:
            _logger.error(f"Error parsing XML file: {e}")
            return None
        root = tree.getroot()

        endpoints = {}
        for server in root.findall('server'):
            ipaddr = server.find('ipaddr').text
            port = int(server.find('port').text)
            serveralias = server.find('serveralias').text

            # Create a dictionary to store the server's endpoints
            server_endpoints = {}
            for endpoint in server.find('endpoints').findall('endpoint'):
                name = endpoint.find('name').text
                function = endpoint.find('function').text
                address = int(endpoint.find('address').text)
                quantity = int(endpoint.find('quantity').text)
                offset = int(endpoint.find('offset').text)
                type = endpoint.find('type').text
                description = endpoint.find('description').text

                # Create a dictionary to store the endpoint details
                endpoint_details = {
                    'name': name,
                    'function': function,
                    'address': address,
                    'quantity': quantity,
                    'offset': offset,
                    'type': type,
                    'description': description
                }
                server_endpoints[name] = endpoint_details

            # Add the server's endpoints to the endpoints dictionary
            endpoints[(ipaddr, port, serveralias)] = server_endpoints
        return endpoints