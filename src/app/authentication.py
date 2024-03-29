from __future__ import annotations

import logging

from fastapi import HTTPException, Depends, Request
from google.auth.transport import requests
from google.oauth2 import id_token

from app.database import get_db
from app.settings import GOOGLE_CLIENT_ID, ADMIN_ROLE
from core.schemas import User
from core.schemas.user import UserRole

logger = logging.getLogger("app.authentication")


def verify_google_token(token: str) -> dict | None:
    try:
        # Verify the token with Google
        id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID,
                                               clock_skew_in_seconds=10)

        # Extract relevant user information from the verified token
        user_info = {
            "sub": id_info.get("sub"),  # Subject (user ID)
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "given_name": id_info.get("given_name"),  # First name
            "family_name": id_info.get("family_name"),
            "picture": id_info.get("picture"),
            # Add more fields as needed
        }

        return user_info

    except ValueError as e:
        # Token verification failed
        logger.info(f"Token verification failed: {e}")
        return None


async def authenticated_user(request: Request, db=Depends(get_db)) -> User:
    user_is_authenticated = request.state.is_authenticated
    if not user_is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication is required to access this resource")
    request_user = request.state.authenticated_user
    user_collection = db.get_collection("user")
    user = await user_collection.get(request_user.email)

    if user is None or user != request_user:
        raise HTTPException(status_code=401, detail="Credentials user is invalid")
    return user


async def authenticated_admin(user: User = Depends(authenticated_user)):
    # user is coroutine, I have to execute the method instead

    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You do not have permission to access this resource")
    return user
