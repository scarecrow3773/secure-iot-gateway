import hashlib
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import logging

_logger = logging.getLogger(__name__)

sys.path.insert(0, "..")
base =             Path(__file__).parent

# TODO: Add OPC UA User Management Roles (Anonymous, AuthenticatedUser, TrustedApplication, Observer, Operator, Engineer, Supervisor, ConfigureAdmin, SecurityAdmin)
# TODO: stick with authorization.xml and individual user assignment without specific roles

class UserManagerXML:
    def __init__(self, user_filename='users.txt', authorization_filename='request-authorization.xml'):
        self._user_filename = Path(base / user_filename)
        self._users = {}
        self._load_users()
        self._authorization_map, self.parameters = self._parse_authorization_file(Path(base / authorization_filename))

    def _load_users(self):
        if os.path.exists(self._user_filename):
            with open(self._user_filename, 'r') as file:
                for line in file:
                    username, hashed_password = line.strip().split(':')
                    self._users[username] = hashed_password
        else:
            with open(self._user_filename, 'w') as file:
                pass

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _parse_authorization_file(self, xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        parameters_dict = {}
        
        for parameter in root.findall('parameter'):
            param_name = parameter.find('name').text
            modifications = []
            
            for modification in parameter.findall('modification'):
                action = modification.find('action').text
                authorized_users = [user.text for user in modification.findall('authorizedUser')]
                modifications.append({
                    'action': action,
                    'authorizedUsers': authorized_users
                })
            
            parameters_dict[param_name] = modifications
        
        #return parameters_dict, 
        return parameters_dict, list(parameters_dict.keys())


    def add_user(self, username, password):
        if username in self._users:
            _logger.warning(f"User '{username}' already exists")
            raise ValueError("User already exists")
        hashed_password = self._hash_password(password)
        self._users[username] = hashed_password
        with open(self._user_filename, 'a') as file:
            file.write(f"{username}:{hashed_password}\n")

    def verifiy_user_authorization(self, username, password, parameter_name, action):
        if parameter_name not in self._authorization_map:
            _logger.warning(f"Parameter '{parameter_name}' not found in authorization map")
            return False
        if username not in self._users:
            _logger.warning(f"User '{username}' not found in user list")
            return False
        for modification in self._authorization_map[parameter_name]:
            if modification['action'] == action and username in modification['authorizedUsers']:
                _logger.info(f"User '{username}' authorized to perform action '{action}' on parameter '{parameter_name}'")
                return self._verify_user(username, password)
            elif modification['action'] == action:
                _logger.info(f"User '{username}' not authorized to perform action '{action}' on parameter '{parameter_name}'")
        return False

    def _verify_user(self, username, password):
        if username not in self._users:
            _logger.warning(f"User '{username}' not found in user list")
            return False
        hashed_password = self._hash_password(password)
        return self._users[username] == hashed_password

    def delete_user(self, username):
        if username not in self._users:
            _logger.warning(f"User '{username}' not found in user list")
            raise ValueError("User does not exist")
        del self._users[username]
        with open(self._user_filename, 'w') as file:
            for user, hashed_password in self._users.items():
                file.write(f"{user}:{hashed_password}\n")

# Test
def main():
    user_manager = UserManagerXML()
    print(f"{user_manager._authorization_map}")

    # Add a new user
    try:
        user_manager.add_user('testuser', 'password123')
        print("User 'testuser' added successfully.")
    except ValueError as e:
        print(e)

    # try:
    #     user_manager.add_user('Administrator', 'Administrator')
    #     user_manager.add_user('Operator1', 'Operator1')
    #     user_manager.add_user('SafetyOperator', 'SafetyOperator')
    #     user_manager.add_user('Chris Schieren', 'ChrisSchieren2025')
    #     print("Users added successfully.")
    # except ValueError as e:
    #     print(e)

    # Verify the user
    if user_manager._verify_user('testuser', 'password123'):
        print("User 'testuser' verified successfully.")
    else:
        print("Failed to verify user 'testuser'.")

    # Delete the user
    try:
        user_manager.delete_user('testuser')
        print("User 'testuser' deleted successfully.")
    except ValueError as e:
        print(e)

    try:
        res = user_manager.verifiy_user_authorization('Administrator', 'Administrator', 'MotorStatus', 'Start')
        print(f"User 'Administrator' authorization: {res}")
        res = user_manager.verifiy_user_authorization('Operator1', 'Operator1', 'MotorStatus', 'Start')
        print(f"User 'Operator1' authorization: {res}")
        res = user_manager.verifiy_user_authorization('SafetyOperator', 'SafetyOperator', 'MotorStatus', 'Start')
        print(f"User 'SafetyOperator' authorization: {res}")
    except ValueError as e:
        print(e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()