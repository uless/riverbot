class MemoryManager:
    def __init__(self):
        self.sessions = {}

    async def create_session(self, session_id):
        self.sessions[session_id] = []

    async def add_message_to_session(self, session_id, message, source_list):
        if session_id not in self.sessions:
            await self.create_session(session_id)

        self.sessions[session_id].append(
            {
                "message":message,
                "source_list":source_list
            }
        )

    async def get_session_history_all(self, session_id, field="message"):
        if session_id in self.sessions:
            return [entry[field] for entry in self.sessions[session_id]]
        else:
            return []
    
    # Look at sessions[session_id], get latest payload, and return source_list
    async def get_latest_source_list(self, session_id, source_field="source_list",message_field="message"):
        try:
            latest_memory_entry=self.sessions[session_id][-1]
            user_query=latest_memory_entry[message_field]["content"]
            source_list=latest_memory_entry[source_field]["sources"]

            return user_query,source_list
        except:
            return None,None
    

    async def format_sources_as_html(self, source_list):
        html = "Here are some of the sources I used for my previous answer:<br>"
        has_items = False
        counter = 1
        for source in source_list:
            human_readable = source["human_readable"]
            url = source["url"]
            if human_readable:  # Skip if human_readable is an empty string
                if url:
                    html += "<br>" + str(counter)  + ". " + human_readable + "<br>" + url
                    has_items=True
                    counter+=1

        if has_items:
            return html
        else:
            return "I did not use any specific sources in providing the information in the previous response."


