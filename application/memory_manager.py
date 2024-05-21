class MemoryManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, session_id):
        self.sessions[session_id] = []

    def add_message_to_session(self, session_id, message):
        if session_id in self.sessions:
            self.sessions[session_id].append(message)
        else:
            self.create_session(session_id)
            self.sessions[session_id].append(message)

    def get_session_history(self, session_id):
        if session_id in self.sessions:
            return self.sessions[session_id]
        else:
            return []