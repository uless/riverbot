class MemoryManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, session_id):
        self.sessions[session_id] = []

    def add_message_to_session(self, session_id, message, source_list):
        if session_id not in self.sessions:
            self.create_session(session_id)

        self.sessions[session_id].append(
            {
                "message":message,
                "source_list":source_list
            }
        )

    def get_session_history_all(self, session_id, field="message"):
        if session_id in self.sessions:
            return [entry[field] for entry in self.sessions[session_id]]
        else:
            return []