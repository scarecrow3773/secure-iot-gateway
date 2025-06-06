import asyncio
import xml.etree.ElementTree as ET
from asyncua import Client, ua
from asyncua.crypto.security_policies import (
    SecurityPolicyBasic128Rsa15,
    SecurityPolicyBasic256,
    SecurityPolicyBasic256Sha256,
    SecurityPolicyAes128Sha256RsaOaep,
SecurityPolicyAes256Sha256RsaPss
)
from asyncua.crypto.validator import CertificateValidator, CertificateValidatorOptions
from asyncua.crypto.truststore import TrustStore
from pathlib import Path
from multiprocessing import shared_memory
import json
import xmlschema
import logging
import os
import time

import posix_ipc
from typing import Optional

_logger = logging.getLogger(__name__)

SECURITY_POLICY_MAP = {
    "SecurityPolicyNone": None,
    "SecurityPolicyBasic128Rsa15": SecurityPolicyBasic128Rsa15,
    "SecurityPolicyBasic256": SecurityPolicyBasic256,
    "SecurityPolicyBasic256Sha256": SecurityPolicyBasic256Sha256,
    "SecurityPolicyAes128Sha256RsaOaep": SecurityPolicyAes128Sha256RsaOaep,
    "SecurityPolicyAes256Sha256RsaPss": SecurityPolicyAes256Sha256RsaPss,
}

class OpcUaClient:
    def __init__(self, server_app_uri: str, client_app_uri: str, alias: str, 
                 security_settings: dict[str, str | None],
                   nodes: list[dict[str, ua.NodeId | str]]):
        self.server_app_uri = server_app_uri
        self.security_settings = security_settings
        self.alias = alias
        self.client = Client(url=server_app_uri)
        self.client.application_uri = client_app_uri
        self.nodes = nodes
        self.connected = False
        self._retry_interval = 5
        self._last_connection_attempt_time = 0

    async def connect(self) -> None:
        cert_base = Path(__file__).parent

        policy = self.security_settings['policy']
        # TODO: User authentication via username and password is not implemented for FreeOpcUa Server. 
        # This is supported by other OSS or commercial OPC UA servers.
        if self.security_settings['username'] is not None and self.security_settings['password'] is not None:
            self.client.set_user(self.security_settings['username'])
            self.client.set_password(self.security_settings['password'])
        if policy == 'SecurityPolicyNone':
            try:
                await self.client.connect()
                self.connected = True
                _logger.warning(f"Connected to {self.server_app_uri}")
            except Exception as e:
                self.connected = False
                _logger.error(f"Error connecting to {self.server_app_uri}.")
        else:
            client_cert = Path(cert_base / self.security_settings['client_certificate'])
            client_private_key = Path(cert_base / self.security_settings['client_private_key'])
            server_cert = Path(cert_base / self.security_settings['server_certificate'])

            await self.client.set_security(
                SECURITY_POLICY_MAP[policy],
                certificate=str(client_cert),
                private_key=str(client_private_key),
                server_certificate=server_cert
            )

            trust_store = TrustStore([Path(cert_base / "certificates/trusted")], [])
            await trust_store.load()
            validator = CertificateValidator(CertificateValidatorOptions.TRUSTED_VALIDATION | CertificateValidatorOptions.PEER_SERVER, trust_store)
            self.client.certificate_validator = validator
            try:
                await self.client.connect()
                self.connected = True
                _logger.info(f"Connected to {self.server_app_uri}")
            except Exception as e:
                self.connected = False
                _logger.error(f"Error connecting to {self.server_app_uri}.")


    # async def retry_connection(self) -> None:
    #     try:
    #         await self.client.connect()
    #         self.connected = True
    #         _logger.info(f"Connected to {self.server_app_uri}")
    #     except Exception as e:
    #         self.connected = False
    #         _logger.error(f"Error connecting to {self.server_app_uri}.")
    async def retry_connection(self) -> None:
        """
        Retry to connect to the OPC UA server with a minimum interval between attempts.
        """
        current_time = time.time()
        if current_time - self._last_connection_attempt_time < self._retry_interval:
            return  # Do not attempt to reconnect if the retry interval has not passed
        
        self._last_connection_attempt_time = current_time  # Update the last connection attempt time
        
        try:
            await self.client.connect()
            self.connected = True
            _logger.info(f"(Re)connection to {self.server_app_uri} successful.")
        except Exception as e:
            self.connected = False
            _logger.error(f"Reconnection to {self.server_app_uri} failed.")


    async def read_value(self, node_id: ua.NodeId) -> tuple[str | None, Optional[any], str | None]: # BUG: Why we have to use Optional[any] instead of any? idk...
        """
        Read a value from an OPC UA node
        :param node_id: The OPC UA node ID to read from
        :return: Tuple of (browse_name, value, varType) or (None, None, None) if there was an error
        """
        try:
            node = self.client.get_node(node_id)
            qualified_name = await node.read_browse_name()
            browse_name = f"{qualified_name.NamespaceIndex}:{qualified_name.Name}"
            value = await node.get_value()
            datatype = await node.read_data_value()
            varType = datatype.Value.VariantType.name
            return browse_name, value, varType
        except Exception as e:
            _logger.error(f"Error reading value from {node_id}.")
            return None, None, None

    async def write_value(self, node_id: ua.NodeId, value: any) -> None:
        """
        Write a value to an OPC UA node
        :param node_id: The OPC UA node ID to write to
        :param value: The value to write
        """
        try:
            node = self.client.get_node(node_id)
            await node.set_value(value)
        except Exception as e:
            _logger.error(f"Error writing value to {node_id}.")

    async def disconnect(self) -> None:
        await self.client.disconnect()
        _logger.warning(f"Disconnected from {self.server_app_uri}")

class OpcUaClientManager:
    def __init__(self, xml_config_path: str | Path, xsd_path: str | Path):
        self.xml_config_path = str(xml_config_path)
        self.xsd_path = str(xsd_path)
        self.clients: list[OpcUaClient] = self.parse_clients()

    def parse_clients(self) -> list[OpcUaClient]:
        """
        Parse the XML configuration file and create a list of OPC UA clients
        :return: A list of OPC UA clients
        """
        schema = xmlschema.XMLSchema(self.xsd_path)
        if not schema.is_valid(self.xml_config_path):
            _logger.error("The XML file does not conform to the provided XSD schema.")

        try:
            tree = ET.parse(self.xml_config_path)
            print(f"Size of OPC UA XML file:        {os.path.getsize(self.xml_config_path)}")
        except (ET.ParseError, FileNotFoundError) as e:
            _logger.error(f"Error parsing XML file: {e}")
            return []

        root = tree.getroot()
        clients = []
        for server in root.findall('server'):
            server_app_uri = server.find('server_app_uri').text
            client_app_uri = server.find('client_app_uri').text
            alias = server.find('alias').text

            security = server.find('security')
            security_settings = {
                'policy': security.find('policy').text,
                'mode': security.find('mode').text,
                'client_certificate': security.find('client_certificate').text if security.find('client_certificate') is not None else None,
                'client_private_key': security.find('client_private_key').text if security.find('client_private_key') is not None else None,
                'server_certificate': security.find('server_certificate').text if security.find('server_certificate') is not None else None,
                'username': security.find('username').text if security.find('username') is not None else None,
                'password': security.find('password').text if security.find('password') is not None else None
            }

            nodes = []
            for node in server.findall('nodes/node'):
                node_info = {
                    'node_id': ua.NodeId(int(node.find('Identifier').text), int(node.find('NamespaceIndex').text)),
                    'datatype': node.find('datatype').text,
                    'description': node.find('description').text
                }
                nodes.append(node_info)

            client = OpcUaClient(server_app_uri, client_app_uri, alias, security_settings, nodes)
            clients.append(client)
        return clients

    async def start_clients(self) -> list[None]:
        """
        Connect to all OPC UA servers
        :return: A list of futures for the connection attempts
        """
        future_list = await asyncio.gather(*(client.connect() for client in self.clients))
        return future_list


    async def periodic_read(self, interval: float,
                            shm_list: list[shared_memory.SharedMemory],
                            semaphore_list: list[posix_ipc.Semaphore]) -> None:
        """
        Periodically read values from OPC UA nodes and write them to shared memory
        :param interval: Time between reads in seconds
        :param shm_list: List of shared memory objects to write to
        :param semaphore_list: List of semaphores for synchronizing access to shared memory
        """
        client: OpcUaClient
        while True:
            opcua_values = {}
            for client in self.clients:
                if not client.connected:
                    await client.retry_connection()
                    if not client.connected:
                        opcua_values[f"OPC UA Connections:{client.alias}"] = {
                                                     "value": client.connected,
                                                     "varType": "Boolean",
                                                     "description": "Connection status to the OPC UA server"
                                                 }
                else:
                    opcua_values[f"OPC UA Connections:{client.alias}"] = {
                                                    "value": client.connected,
                                                    "varType": "Boolean",
                                                    "description": "Connection status to the OPC UA server"
                                                }
                    for node in client.nodes:
                        value = None
                        browse_name = None
                        if node['datatype'] != 'Object':
                            browse_name, value, datatype = await client.read_value(node['node_id'])
                            if value is not None:
                                opcua_values[browse_name] = {
                                                            "value": value,
                                                            "varType": str(datatype),
                                                            "description": f"{node['description']}"
                                                        }
                            else:
                                _logger.error(f"Error reading value from {node['node_id']}")
                                opcua_values[browse_name] = {
                                                            "value": "Error reading value",
                                                            "varType": "String",
                                                            "description": f"{node['description']}"
                                                        }
            # Write the opcua_values to shared memory with semaphore protection
            for shm, sem in zip(shm_list, semaphore_list):
                sem: posix_ipc.Semaphore
                shm: shared_memory.SharedMemory

                sem.release()
                await asyncio.sleep(0.01)
                sem.acquire()
                shm_size = shm.size
                opcua_values_json = json.dumps(opcua_values)
                shm.buf[:shm_size] = b'\x00' * shm_size  # Clear the shared memory buffer
                shm.buf[:len(opcua_values_json)] = opcua_values_json.encode('utf-8')
                if len(opcua_values_json)/shm_size > 0.9: # Log a warning if the shared memory is more than 90% full
                    _logger.warning(f"ModbusTCP Shared Memory     {len(opcua_values_json)}/{shm_size} bytes used (more than 90% full).")
                sem.release()
            await asyncio.sleep(interval)

    async def stop_clients(self) -> None:
        """
        Disconnect from all OPC UA servers
        """
        await asyncio.gather(*(client.disconnect() for client in self.clients))

if __name__ == "__main__":
    _logger.info("This is the OPC UA Client Manager module")