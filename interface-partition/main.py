import asyncio
import logging
import os

# Own modules
from interface_setup import setup_opcua_server
from data_manager import DataManager
#from user_manager_xml import UserManagerXML # Deprecated
#from user_manager import UserManager
#from authorization_handler import AuthorizationHandler

import posix_ipc
import random
import threading

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
path = os.path.dirname(os.path.abspath(__file__))
# credentials_db_path = os.path.join(path, "user_manager/credentials.db")
# casbin_model_path_res = os.path.join(path, "authorization_handler/rbac_with_resource_roles_model.conf")
# casbin_policy_path_res = os.path.join(path, "authorization_handler/rbac_with_resource_roles_policy.csv")


async def send_vor_request(mq:posix_ipc.MessageQueue, request:str):
    # Initial filling of the message queue:
    for i in range(10):
        prio = random.randint(0, 31)
        mq.send(request.encode(), timeout=None, priority=prio)
        _logger.error(f"Filled mq with request: {request} with priority: {prio}")

    while True:
        try:
            prio = random.randint(0, 10)
            #rq = f"{request}:{prio}"
            #mq.send(rq.encode(), prio)
            #mq.send(rq.encode(), timeout=None, priority=prio)
            mq.send(request.encode(), timeout=None, priority=prio)

            _logger.error(f"Request sent: {request} with priority: {prio}")
        except Exception as e:
            _logger.error(f"Error sending request: {e}")
        await asyncio.sleep(2)
    

async def main():
    # user_manager_xml = UserManagerXML()
    # list_vor_parameters = user_manager_xml.parameters
    list_vor_parameters = None

    # Initialize components # MOVED to server_methods.py
    # rbac_handler = AuthorizationHandler(casbin_model_path_res, casbin_policy_path_res)
    # user_manager = UserManager(credentials_db_path)

    #server = await setup_opcua_server()
    server = await setup_opcua_server(list_vor_parameters)
    await asyncio.sleep(5)

    opcua_shm_name = 'opcua_shm_interface'
    opcua_sem_name = 'opcua_semaphore_interface'
    modbus_shm_name = 'modbus_shm_interface'
    modbus_sem_name = 'modbus_semaphore_interface'

    # Initial shared memory reading for OPC UA Server setup
    opcua_variables = []
    data_manager = DataManager(server, opcua_shm_name, opcua_sem_name, modbus_shm_name, modbus_sem_name)

    # Setup POSIX message queue for ipc with the intermediate VoR partition
    # try:
    #     mq = posix_ipc.MessageQueue("/interface_partition_mq", posix_ipc.O_CREX)
    # except Exception as e:
    #     _logger.error(f"Error creating POSIX message queue: {e}")

    _logger.warning("OPC UA Server of the interface partition is running.")
    async with server:
        try:
            # Initial population of OPC UA Server
            #opcua_variables, modbus_variables = await data_manager.populate_opcua_server()
            opcua_variables = await asyncio.create_task(data_manager.create_opcua_population())
            print(f"OPC UA: {opcua_variables}")
            modbus_variables = await asyncio.create_task(data_manager.create_modbus_population())
            print(f"ModbusTCP: {modbus_variables}")

            # Periodic update of OPC UA Server
            #periodic_update = asyncio.create_task(data_manager.update_server_objects(opcua_variables, modbus_variables))
            periodic_update_opcua = asyncio.create_task(data_manager.update_population_from_opcua_shm(opcua_variables))
            periodic_update_modbus_tcp = asyncio.create_task(data_manager.update_population_from_modbus_tcp_shm(modbus_variables))
            #periodic_vor_request = asyncio.create_task(send_vor_request(mq, "Test Request"))

            await asyncio.gather(periodic_update_opcua, periodic_update_modbus_tcp)
            #await asyncio.gather(periodic_update, periodic_vor_request)

            # # Try threading the OPC UA and ModbusTCP service:
            # threads = []
            # opcua_thread = threading.Thread(target=data_manager.thread_update_opcua_objects(opcua_variables))
            # threads.append(opcua_thread)
            # modbus_thread = threading.Thread(target=data_manager.thread_update_modbus_tcp_objects(modbus_variables))
            # threads.append(modbus_thread)
            # for thread in threads:
            #     thread.start()
            # for thread in threads:
            #     thread.join()

        except asyncio.CancelledError:
            _logger.error("asyncio.CancelledError")

        except KeyboardInterrupt:
            #periodic_update.cancel()
            periodic_update_opcua.cancel()
            periodic_update_modbus_tcp.cancel()
            #periodic_vor_request.cancel()
            _logger.error("KeyboardInterrupt")

        finally:
            _logger.info("Tasks stopped")


if __name__ == "__main__":
    asyncio.run(main())