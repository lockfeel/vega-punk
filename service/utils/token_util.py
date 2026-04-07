# -*- coding: utf-8 -*-
import time
from typing import Optional, Dict

import jwt

SECRET_KEY = "com.amemo.app.cipher"
ALGORITHM = "HS256"


def generateToken(userId: str, expireSeconds: int = 2592000) -> str:
    payload = {
        "userId": userId,
        "exp": int(time.time()) + expireSeconds,
        "iat": int(time.time())
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verifyToken(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "userId": payload.get("userId"),
            "expireTime": payload.get("exp"),
            "issuedAt": payload.get("iat")
        }
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def getUserIdFromToken(token: str) -> Optional[str]:
    result = verifyToken(token)
    return result.get("userId") if result else None


def refreshToken(token: str, extendSeconds: int = 2592000) -> Optional[str]:
    result = verifyToken(token)
    if not result:
        return None
    return generateToken(result["userId"], extendSeconds)


def isTokenExpired(token: str) -> bool:
    result = verifyToken(token)
    return result is None
