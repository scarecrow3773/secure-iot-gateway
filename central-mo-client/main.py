from test_requests  import generate_request_parameters, create_request_arguments, add_users_to_user_manager
from asyncua import Client, ua
import asyncio
import logging
from asyncua.crypto.security_policies import SecurityPolicyAes256Sha256RsaPss
from asyncua.crypto.validator import CertificateValidator, CertificateValidatorOptions
from asyncua.crypto.truststore import TrustStore
from asyncua.ua import StatusCode, StatusCodes

from pathlib import Path

_logger = logging.getLogger(__name__)

async def submit_request(client: Client, in_args, params):
    """Submit the request to the server and log results"""
    try:
        # Find the method node
        objects = client.nodes.objects
        child = await objects.get_child(['2:RequestHandler'])
        
        _logger.warning(f"Submit request with priority {params['priority']} at {params['timestamp']}")
        
        # Call the method
        try:
            result = await child.call_method("2:request", *in_args)
            
            # Parse output arguments
            _logger.info(f"Result: {result}")
            request_id, server_timestamp, notification = result
        except Exception as e:
            _logger.error(f"Error calling method: {e}")
            return None
        # partially matching string:
    
        # if "Authentication failed" in notification:
        #     _logger.error(f"Authentication failed for issuer {params['issuer_id']} with credentials {params['credentials']}")
        # if "Authorization failed" in notification:
        #     _logger.error(f"Authorization failed for issuer {params['issuer_id']} with parameters {params['parameters']} and modification {params['modification']}")
        if "Submission received" in notification:
            _logger.info(f"Submission received for request {request_id} for issuer {params['issuer_id']} with parameters {params['parameters']} and modification {params['modification']}")

        _logger.info(f"Request ID:       {request_id}")
        _logger.info(f"Server Timestamp: {server_timestamp}")
        _logger.info(f"Notification:     {notification}")
        
        return result
    except Exception as e:
        _logger.error(f"Error calling method: {e}")
        return None
    
async def call_add_user_method(client: Client, admin: dict, users: dict):
    """Call the add user method on the server"""

    admin_id = list(admin.keys())[0]
    admin_credentials = admin[admin_id]
    try:
        # Find the method node
        objects = client.nodes.objects
        child = await objects.get_child(['2:UserManager'])
        
        for user, password in users.items():
            _logger.info(f"Adding user {user} with password {password}")
            try:
                res = await child.call_method("2:add_user",ua.Variant(admin_id, ua.VariantType.String), ua.Variant(admin_credentials, ua.VariantType.String), ua.Variant(user, ua.VariantType.String), ua.Variant(password, ua.VariantType.String))
                ua_status_code, ua_status_message = res
                if str(ua_status_code) != str(StatusCode(StatusCodes.Good)):
                    _logger.warning(f"Error adding user {user} with credentials {password}: {ua_status_message}")
                _logger.info(f"Method called for user {user} with credentials {password}: Result {res}")
            except Exception as e:
                _logger.error(f"Error calling method for user {user} with credentials {password}: {e}")
        # Call the method
        # result = await child.call_method("2:add_user", *users)
        # _logger.info(f"Method called")
        return True
    except Exception as e:
        _logger.error(f"Error calling method: {e}")
        return None
    
async def clear_database(client: Client, admin: dict, users: dict):
    """Call the clear database method on the server"""
    admin_id = list(admin.keys())[0]
    admin_credentials = admin[admin_id]
    try:
        # Find the method node
        objects = client.nodes.objects
        child = await objects.get_child(['2:UserManager'])
        
        _logger.info(f"Clearing user manager database")
        for user, password in users.items():
            _logger.info(f"Clearing user {user} with password {password}")
            try:
                res = await child.call_method("2:remove_user",ua.Variant(admin_id, ua.VariantType.String), ua.Variant(admin_credentials, ua.VariantType.String), ua.Variant(user, ua.VariantType.String))
                ua_status_code, ua_status_message = res
                if str(ua_status_code) != str(StatusCode(StatusCodes.Good)):
                    _logger.error(f"Error clearing database: {ua_status_message}")
                _logger.info(f"Method called for user {user} with credentials {password}: Result {res}")
            except Exception as e:
                _logger.error(f"Error calling method for user {user} with credentials {password}: {e}")
    except Exception as e:
        _logger.error(f"Error calling method: {e}")
        return None

async def setup_client(max_retries=5, retry_delay=5):
    """Setup and connect to OPC UA client with security"""
    _logger.info(f"Central M+O Application started.")

    url = "opc.tcp://interface-partition:4840/freeopcua/server/"  # Ensure this matches the server address

    cert_base = Path(__file__).parent
    client_cert = Path(cert_base / "certificates/python_client/mo_client_cert.der")
    client_private_key = Path(cert_base / "certificates/python_client/mo_client_key.pem")
    server_cert = Path(cert_base / "certificates/trusted/server_cert.der")

    client = Client(url)
    # Set a reasonable timeout for operations
    client.session_timeout = 30000  # 30 seconds in milliseconds
    
    await client.set_security(
        SecurityPolicyAes256Sha256RsaPss,
        certificate=str(client_cert),
        private_key=str(client_private_key),
        server_certificate=server_cert
    )
    
    trust_store = TrustStore([Path(cert_base / "certificates/trusted")], [])
    await trust_store.load()
    validator = CertificateValidator(CertificateValidatorOptions.TRUSTED_VALIDATION | CertificateValidatorOptions.PEER_SERVER, trust_store)
    client.certificate_validator = validator

    # Implement retry logic for connecting to the server
    for attempt in range(max_retries):
        try:
            _logger.info(f"Attempting to connect to OPC UA server (Attempt {attempt+1}/{max_retries})")
            # Use a reasonable timeout for the connection attempt
            await asyncio.wait_for(client.connect(), timeout=10)
            _logger.info("Successfully connected to OPC UA server")
            return client
        except asyncio.TimeoutError:
            _logger.warning(f"Connection attempt {attempt+1} timed out")
        except Exception as e:
            _logger.error(f"Connection attempt {attempt+1} failed: {e}")
        
        if attempt < max_retries - 1:
            _logger.info(f"Waiting {retry_delay} seconds before retry...")
            await asyncio.sleep(retry_delay)
    
    _logger.error(f"Failed to connect after {max_retries} attempts")
    raise ConnectionError(f"Could not connect to OPC UA server at {url}")

async def is_client_connected(client):
    """Check if client is still connected and operational"""
    try:
        # Simple test to check if the connection is still alive
        await asyncio.wait_for(client.nodes.server_state.read_value(), timeout=5)
        return True
    except Exception:
        return False

async def main():
    """Main function to execute request submissions in a loop"""
    client = None
    try:
        client = await setup_client()
        
        admin, users = add_users_to_user_manager()
        await call_add_user_method(client, admin, users)
        
        calls = 0
        while calls < 3600:
            try:
                # Check the connection before attempting operations
                if not await is_client_connected(client):
                    _logger.warning("Connection lost. Attempting to reconnect...")
                    await client.disconnect()
                    client = await setup_client()
                
                try:
                    params = generate_request_parameters()

                except Exception as e:
                    _logger.error(f"Error generating request parameters: {e}")
                    continue
                in_args = create_request_arguments(params)
                await submit_request(client, in_args, params)
            except Exception as e:
                _logger.error(f"Error in request cycle: {e}")  
            calls += 1          
            await asyncio.sleep(1)  # Increased sleep to reduce load on server
        #res = await clear_database(client, admin, users)
        #_logger.error(f"Database cleared: {res}")
    except Exception as e:
        _logger.error(f"Main loop error: {e}")
    finally:
        if client:
            try:
                await client.disconnect()
            except Exception as e:
                _logger.error(f"Error disconnecting client: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main())