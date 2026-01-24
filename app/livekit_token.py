import os
from livekit import api

def generate_livekit_token(room_name: str, participant_identity: str) -> str:
    """ Generate a LiveKit JWT token for a participant to join a room. """
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        raise ValueError("LIVEKIT_API_KEY or LIVEKIT_API_SECRET not set in environment.")

    token = api.AccessToken(api_key, api_secret) \
        .with_identity(participant_identity) \
        .with_name(participant_identity) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
        ))
    
    return token.to_jwt()
