import asyncio
import logging
import sys
from pathlib import Path
from multiprocessing import shared_memory
import threading
import posix_ipc

# local imports
from opcua_client import OpcUaClientManager
from modbus_tcp_client import ModbusClientManager

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

async def opcua_service() -> None:
    """
    This function starts the OPC UA service and reads the data from the OPC UA server.
    """
    sys.path.insert(0, "..")
    path_base = Path(__file__).parent
    xml_config_file_opcua =  Path(path_base / "config/opcua-endpoints_factory.xml")
    xsd_file_opcua = Path(path_base / "config/opcua-endpoints.xsd")

    opcua_interval = 1 # Interval in seconds
    opcua_shm_name = 'opcua_shm'
    opcua_shm_size = 1024*10
    opcua_semaphore_name = 'opcua_semaphore'

    # Prepare lists for shm and semaphore
    opcua_shm_psmo = shared_memory.SharedMemory(name=f"{opcua_shm_name}_psmo", create=True, size=opcua_shm_size)
    opcua_shm_interface = shared_memory.SharedMemory(name=f"{opcua_shm_name}_interface", create=True, size=opcua_shm_size)
    opcua_shm_list = [opcua_shm_psmo, opcua_shm_interface]
    
    opcua_semaphore_psmo = posix_ipc.Semaphore(f"{opcua_semaphore_name}_psmo", posix_ipc.O_CREX)
    opcua_semaphore_interface = posix_ipc.Semaphore(f"{opcua_semaphore_name}_interface", posix_ipc.O_CREX)
    opcua_sem_list = [opcua_semaphore_psmo, opcua_semaphore_interface]

    opcua_manager = OpcUaClientManager(xml_config_file_opcua, xsd_file_opcua)
    if await opcua_manager.start_clients() == []:
        _logger.error(f"Start clients returned empty list.")
        return
    await opcua_manager.periodic_read(opcua_interval, opcua_shm_list, opcua_sem_list)

def opcua_service_thread() -> None:
    """
    This function starts the OPC UA service in a new thread.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(opcua_service())
    loop.close()

async def modbus_tcp_service() -> None:
    """
    This function starts the Modbus TCP service and reads the data from the Modbus TCP server.
    """
    sys.path.insert(0, "..")
    path_base = Path(__file__).parent
    xml_config_file_modbustcp =  Path(path_base / "config/modbustcp-endpoints_ecotec-rpi.xml")
    xsd_file_modbustcp = Path(path_base / "config/modbustcp-endpoints.xsd")

    modbus_interval = 1
    modbus_shm_name = 'modbus_shm'
    modbus_shm_size = 1024*12
    modbus_semaphore_name = 'modbus_semaphore'

    # Prepare lists for shm and semaphore
    modbus_shm_psmo = shared_memory.SharedMemory(name=f"{modbus_shm_name}_psmo", create=True, size=modbus_shm_size)
    modbus_shm_interface = shared_memory.SharedMemory(name=f"{modbus_shm_name}_interface", create=True, size=modbus_shm_size)
    modbus_shm_list = [modbus_shm_psmo, modbus_shm_interface]
    
    modbus_semaphore_psmo = posix_ipc.Semaphore(f"{modbus_semaphore_name}_psmo", posix_ipc.O_CREX)
    modbus_semaphore_interface = posix_ipc.Semaphore(f"{modbus_semaphore_name}_interface", posix_ipc.O_CREX)
    modbus_sem_list = [modbus_semaphore_psmo, modbus_semaphore_interface]

    modbus_manager = ModbusClientManager(xml_config_file_modbustcp, xsd_file_modbustcp)
    await modbus_manager.start_clients()
    await modbus_manager.periodic_read(modbus_interval, modbus_shm_list, modbus_sem_list)

def modbus_tcp_service_thread() -> None:
    """
    This function starts the Modbus TCP service in a new thread.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(modbus_tcp_service())
    loop.close()

async def main():
    await asyncio.sleep(3)

    threads = []
    opcua_thread = threading.Thread(target=opcua_service_thread)
    threads.append(opcua_thread)
    modbus_thread = threading.Thread(target=modbus_tcp_service_thread)
    threads.append(modbus_thread)

    try:
        print("CPC-Partition is running.")
        thread: threading.Thread = None
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        _logger.info("Clients stopped")

if __name__ == "__main__":
    asyncio.run(main())