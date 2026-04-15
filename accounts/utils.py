from .models import Conversation

def get_or_create_conversation(user1, user2):
    conversations = Conversation.objects.filter(participants=user1).filter(participants=user2)
    if conversations.exists():
        return conversations.first()
    conversation = Conversation.objects.create()
    conversation.participants.add(user1, user2)
    return conversation

    
