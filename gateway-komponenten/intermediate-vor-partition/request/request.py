import uuid

class Request:
    def __init__(self, issuer_id, request_id, timestamp,
                 description, impact, parameters, modification, priority = None):
        self.id = str(uuid.uuid4())     #Request_ID
        self.issuer_id = issuer_id      #Mandatory
        self.request_id = request_id     #unique identifier for the request
        self.timestamp = timestamp     #M, timestamp of request generation
        #self.credentials = credentials      #M
        #self.issuer_characteristics = issuer_characteristics    #Recommended
        self.description = description  # Mandatory field (Human-readable Verification Result)
        self.impact = impact  # Mandatory field (Impact and benefits)
        self.parameters = parameters  # Mandatory field (Model parameters)
        self.modification = modification  # Mandatory field (Machine-readable description of changes); need to express whether it is relative or absolute change; unit
        self.priority = priority
        self.Request_verified_status = False

    # Process requests based on their priority 
    def __lt__(self, other):
        if self.priority and other.priority:
            return self.priority < other.priority   #Lower priority number first
        return self.timestamp < other.timestamp  # FIFO if priorities are equal or absent
