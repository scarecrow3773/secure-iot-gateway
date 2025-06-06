import logging
import queue
import time

from psmo_shm_handler import OPCUA_Thread, ModbusTCP_Thread

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# TODO: Decide on message queuing strategy!
def main():
    time.sleep(7)
    opcua_shm_name = 'opcua_shm_psmo'
    opcua_semaphore_name = 'opcua_semaphore_psmo'
    opcua_queue = queue.Queue(maxsize=5)
    opcua_thread = OPCUA_Thread(opcua_semaphore_name, opcua_shm_name, opcua_queue)

    modbus_shm_name = 'modbus_shm_psmo'
    modbus_semaphore_name = 'modbus_semaphore_psmo'
    modbus_queue = queue.Queue(maxsize=5)
    modbus_thread = ModbusTCP_Thread(modbus_semaphore_name, modbus_shm_name, modbus_queue)

    opcua_thread.start()
    modbus_thread.start()

    try:
        print("psM+O partition is running.")
        while True:
            if not opcua_queue.empty():
                #_logger.info(f"main processing could be done here...")
                item = opcua_queue.get()
                item_count = len(item.keys())
                _logger.info(f"Retrieved {item_count} items from OPC UA queue. Waiting to process...")
            if not modbus_queue.empty():
                #_logger.info(f"main processing could be done here...")
                item = modbus_queue.get()
                item_count = len(item.keys())
                _logger.info(f"Retrieved {item_count} items from ModbusTCP queue. Waiting to process...")
            #time.sleep(.05)
    except Exception as e:
        _logger.error(f"Error handling main-process: {e}")
    except KeyboardInterrupt:
        opcua_thread.stop()
        modbus_thread.stop()
        opcua_thread.join()
        modbus_thread.join()

if __name__ == "__main__":
    main()