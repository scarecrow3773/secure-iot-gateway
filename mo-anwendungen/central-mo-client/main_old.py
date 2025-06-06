import asyncio
import logging
import datetime
from asyncua import Client, ua
from asyncua.crypto.security_policies import SecurityPolicyAes256Sha256RsaPss
from asyncua.crypto.validator import CertificateValidator, CertificateValidatorOptions
from asyncua.crypto.truststore import TrustStore
from pathlib import Path

import random

logging.basicConfig(level=logging.ERROR)
_logger = logging.getLogger(__name__)

async def call_submit_request():
    await asyncio.sleep(10)
    print(f"Central M+O Application started.")

    url = "opc.tcp://interface-partition:4840/freeopcua/server/"  # Ensure this matches the server address

    cert_base = Path(__file__).parent
    client_cert = Path(cert_base / "certificates/python_client/mo_client_cert.der")
    client_private_key = Path(cert_base / "certificates/python_client/mo_client_key.pem")
    server_cert = Path(cert_base / "certificates/trusted/server_cert.der")

    #async with Client(url) as client:
    client = Client(url)
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

    await client.connect()

    while True:
        try:
            # Find the method node
            #obj = await client.nodes.objects.get_child(["2:RequestHandler"])
            objects = client.nodes.objects
            child = await objects.get_child(['2:RequestHandler'])
            
            # Prepare input arguments
            issuer_id_examples = [
                "Python-M+O-Client",
                "UA-Expert-Client",
                "Workflow-Optimizer-Service",
                "Historian-Service",
                "Data-Analyzer-Service"
            ]
            credential_examples = [
                "MyPassword123",
                "AdminAdmin",
                "SecurePassword",
                "WSkjcrv73&$bde"
            ]

            user_password_map = {
                # authenticated users, partially authorized
                "john": "Admin123_secure_password_2025",    # pre-existing user with Admin-role
                "sarah": "Sarah123_secure_password_2025",   # pre-existing user with PlantOperator-role
                "mike": "Mike123_secure_password_2025",     # this user does not exist by default in the user-manager, but in rbac as MaintenancePersonnel
                "david": "David123_secure_password_2025",   # this user does not exist by default in the user-manager, but in rbac as PlantOperator
                "lisa": "Lisa123_secure_password_2025",     # this user does not exist by default in the user-manager, but in rbac as MaintenancePersonnel
                "horst": "WSkjcrv73&$bde",                  # this user does not exist in the rbac
                # unauthenticated and unauthorized users
                "gunter": "UZUD875$$§jbojob37530",           # this user does not exist in the rbac
                "Python-M+O-Client": "MyPassword",
                "UA-Expert-Client": "AdminAdmin",
                "Workflow-Optimizer-Service": "SecurePassword",
                "Historian-Service": "WSkjcrviedjvbejvb",
                "Data-Analyzer-Service": "WSkjcrv73&$bde"
            }

            timestamp = datetime.datetime.now(datetime.timezone.utc)
            description_examples = [
                "Adjust machine calibration",
                "Enable production line optimization",
                "Update inventory tracking system",
                "Refactor sensor data integration",
                "Enhance production scheduling",
                "Install new automation features",
                "Update system diagnostics",
                "Improve quality control checks"
            ]
            impact_examples = [
                "Increased throughput",
                "Reduced downtime",
                "Improved product quality",
                "Enhanced system reliability",
                "Lower operational costs",
                "Faster production cycles",
                "Improved resource utilization",
                "Higher yield rates"
            ]
            parameter_examples = [ # Ecotec Examples (@Chris Schieren)
                "M2:Kompressor1",
                "AM10:Netzdruck",
                "I9:StoerungKondensat",
                "Q5:StoerungTrockner"
            ]
            modification_examples = [
                "Modify factory system settings",
                "Update production software",
                "Enhance automated assembly line",
                "Refactor data analytics pipeline",
                "Implement new machine learning model",
                "Upgrade system monitoring tools",
                "Improve sensor calibration process",
                "Install new production machinery"
            ]
            parameter_examples_rbac = [ 
                # RBAC Examples
                "Ejector",
                "Drill",
                "Motor",
                "FumeExtractionSystem",
                # not existing in the rbac
                "M2:Kompressor1",
                "AM10:Netzdruck",
                "I9:StoerungKondensat",
                "Q5:StoerungTrockner"
            ]
            modification_examples_rbac = [
                # RBA Examples
                "turn_on",
                "turn_off",
                "extend",
                "retract",
                # not existing in the rbac
                "Modify factory system settings",
                "Update production software",
                "Enhance automated assembly line",
                "Refactor data analytics pipeline"
            ]

            # Randomly select
            #issuer_id = random.choice(issuer_id_examples)
            #credentials = random.choice(credential_examples)
            issuer_id, credentials = random.choice(list(user_password_map.items()))  # select random user
            # timestamp already generated
            description = random.sample(description_examples, random.randint(1, 3))
            impact = random.sample(impact_examples, random.randint(1, 3))
            #parameters = list(random.choice(parameter_examples)) # TODO: Check if paramters need to be a list
            parameters = random.choice(parameter_examples_rbac)
            modification = random.choice(modification_examples_rbac)
            priority = random.randint(0,31)

            # Convert to OPC UA types
            in_args = [
                ua.Variant(issuer_id, ua.VariantType.String),
                ua.Variant(credentials, ua.VariantType.String),
                ua.Variant(timestamp, ua.VariantType.DateTime),
                ua.Variant(description, ua.VariantType.String, [0]),
                ua.Variant(impact, ua.VariantType.String, [0]),
                ua.Variant(parameters, ua.VariantType.String), # TODO: Check if paramters need to be a list
                ua.Variant(modification, ua.VariantType.String),
                ua.Variant(priority, ua.VariantType.Int32),
            ]
            _logger.warning(f"Submit request with priority {priority} at {timestamp}")
            # Call the method
            result = await child.call_method("2:request", *in_args)
            #_logger.warning(f"Method called")
                
            # Parse output arguments
            request_id, server_timestamp, notification = result
            _logger.warning(f"Request ID:       {request_id}")
            _logger.warning(f"Server Timestamp: {server_timestamp}")
            _logger.warning(f"Notification:     {notification}")

        except Exception as e:
            _logger.error(f"Error calling method: {e}")

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(call_submit_request())