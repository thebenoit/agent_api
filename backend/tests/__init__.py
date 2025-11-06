# Pour importer depuis tests/sessions/session_test.py
from .sessions.session_test import test_is_functional


# Pour importer depuis tests/facebook/test.py
from .facebook.test import test_user_text_chat

__all__ = ["test_get_req_info",  
           "test_user_text_chat",
           "graphql_test"]