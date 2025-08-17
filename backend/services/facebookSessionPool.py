





class FacebookSessionPool:
    def __init__(self,max_sessions=50):
        self.max_sessions = max_sessions
        self.db = mongo_manager.get_sync_db()
        self.pool_collection = self.db["session_pool"]
        self.fb_session_model = FacebookSessionModel()
        
        self.pool_collection.create_index("pool_id")
        self.pool_collection.create_index("last_used")
    
    