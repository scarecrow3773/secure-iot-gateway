import logging
import datetime
import random
from asyncua import ua

_logger = logging.getLogger(__name__)

# Global dictionaries for test data
USER_PASSWORD_MAP = {
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

DESCRIPTION_EXAMPLES = [
    # Heikos requests for the VoR1-testing
    # "Adjust machine calibration",
    # "Enable production line optimization",
    # "Update inventory tracking system",
    # "Refactor sensor data integration",
    # "Enhance production scheduling",
    # "Install new automation features",
    # "Update system diagnostics",
    # "Improve quality control checks"

    # Yuanchens requests for the VoR2-testing
    "Update system diagnostics",
    "Enhance production scheduling",
    "Install new automation features",
    "Refactor sensor data integration",
    "Improve quality control checks",
    "Adjust machine calibration",
]

IMPACT_EXAMPLES = [
    # Heikos requests for the VoR1-testing
    # "Increased throughput",
    # "Reduced downtime",
    # "Improved product quality",
    # "Enhanced system reliability",
    # "Lower operational costs",
    # "Faster production cycles",
    # "Improved resource utilization",
    # "Higher yield rates"

    # Yuanchens requests for the VoR2-testing
    # ??? TODO: Consult with Yuanchen
    # "Lower operational costs",
    # "Improved product quality",
    # "Higher yield rates",
    # "Faster production cycles",
    # "Improved resource utilization",
    # "Enhanced system reliability",

    "Motor Speed Configuration",
    "flow rate adjustment",
]

PARAMETER_MODIFICATION_EXAMPLES_RBAC = {
    # Heikos requests for the VoR1-testing
    # "Ejector": ["extend", "retract"],
    # "Drill": ["turn_on", "turn_off"],
    # "Motor": ["turn_on", "turn_off"],
    # "FumeExtractionSystem": ["turn_on", "turn_off"],
    # # not existing in the rbac
    # "M2:Kompressor1": ["turn_on", "turn_off"],
    # "AM10:Netzdruck": ["turn_on", "turn_off"],
    # "I9:StoerungKondensat": ["turn_on", "turn_off"],
    # "Q5:StoerungTrockner": ["turn_on", "turn_off"],

    # Yuanchens requests for the VoR2-testing
    "MotorSpeed_SP": ["750", "900"],
    "Mixer_SP": ["5", "7"],
    "Pump_A_Power": ["9.4", "10.5"],
    "Pump_B_Power": ["9.4", "15.5"],
    "Heater_Power": ["17.5", "20.0"],
}

PARAMETER_EXAMPLES_RBAC = [
    # Heikos requests for the VoR1-testing
    # # RBAC Examples
    # "Ejector",
    # "Drill",
    # "Motor",
    # "FumeExtractionSystem",
    # # not existing in the rbac
    # "M2:Kompressor1",
    # "AM10:Netzdruck",
    # "I9:StoerungKondensat",
    # "Q5:StoerungTrockner",

    # Yuanchens requests for the VoR2-testing
    "MotorSpeed_SP",
    "Mixer_SP",
    "Pump_A_Power",
    "Pump_B_Power",
    "Heater_Power",
]

# Switched to param+mod map
# MODIFICATION_EXAMPLES_RBAC = [
#     # RBA Examples
#     "turn_on",
#     "turn_off",
#     "extend",
#     "retract",
#     # not existing in the rbac
#     "Modify factory system settings",
#     "Update production software",
#     "Enhance automated assembly line",
#     "Refactor data analytics pipeline"
# ]

# def add_users_to_user_manager() -> dict:
#     """Return a tuple with the Admin (first tuple) and the rest of the user-password map"""
#     return list(USER_PASSWORD_MAP.items())[:1],  dict(list(USER_PASSWORD_MAP.items()))[2:len(USER_PASSWORD_MAP)]

def add_users_to_user_manager():
    """Return a tuple with the Admin (first tuple) and the rest of the user-password map"""
    # Get admin user (first item in the dictionary)
    admin = {}
    for admin_k, admin_v in list(USER_PASSWORD_MAP.items())[:1]:
        admin[admin_k] = admin_v
    #admin = list(USER_PASSWORD_MAP.items())[:1]
    
    # Convert remaining items back to a dictionary
    remaining_users = {}
    for k, v in list(USER_PASSWORD_MAP.items())[1:]:
        remaining_users[k] = v
    
    return admin, remaining_users

def generate_request_parameters():
    """Generate random test parameters for a request"""
    issuer_id, credentials = random.choice(list(USER_PASSWORD_MAP.items()))
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    description = random.sample(DESCRIPTION_EXAMPLES, random.randint(1, 3))
    #impact = random.sample(IMPACT_EXAMPLES, random.randint(1, 2))
    impact = random.choice(IMPACT_EXAMPLES)
    parameters = random.choice(PARAMETER_EXAMPLES_RBAC)

    #modification = random.choice(MODIFICATION_EXAMPLES_RBAC)

    param_mod_rbac = PARAMETER_MODIFICATION_EXAMPLES_RBAC.get(parameters)
    if param_mod_rbac:
        modification = random.choice(param_mod_rbac)

    priority = random.randint(0, 31)
    
    return {
        "issuer_id": issuer_id,
        "credentials": credentials,
        "timestamp": timestamp,
        "description": description,
        "impact": impact,
        "parameters": parameters,
        "modification": modification,
        "priority": priority
    }

def create_request_arguments(params):
    """Convert parameters to OPC UA variant types for method call"""
    return [
        ua.Variant(params["issuer_id"], ua.VariantType.String),
        ua.Variant(params["credentials"], ua.VariantType.String),
        ua.Variant(params["timestamp"], ua.VariantType.DateTime),
        ua.Variant(params["description"], ua.VariantType.String, [0]),
        ua.Variant(params["impact"], ua.VariantType.String), # TODO: or list
        ua.Variant(params["parameters"], ua.VariantType.String),
        ua.Variant(params["modification"], ua.VariantType.String),
        ua.Variant(params["priority"], ua.VariantType.Int32),
    ]

if __name__ == "__main__":
    admin, users = add_users_to_user_manager()
    print(admin)
    print(users)
    print(admin.keys()[0])
    print(admin.keys()[1])