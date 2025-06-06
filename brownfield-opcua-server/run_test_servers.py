import asyncio
import multiprocessing
import logging

from opcua_unsecured_server import start_unsecured_server
from opcua_secured_server import start_secured_server

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

def run_unsecured_server():
    asyncio.run(start_unsecured_server())

def run_secured_server():
    asyncio.run(start_secured_server())

if __name__ == "__main__":
    unsecured_process = multiprocessing.Process(target=run_unsecured_server)
    secured_process = multiprocessing.Process(target=run_secured_server)

    try:
        unsecured_process.start()
        secured_process.start()
        print("Brownfield OPC UA Servers started successfully.")
        unsecured_process.join()
        secured_process.join()
    except KeyboardInterrupt:
        print("Shutting down servers...")
        unsecured_process.terminate()
        secured_process.terminate()