"""Step 2 - Get the current user: turn the token into a user through a dependency.

Run:  uvicorn get_current_user:app --reload

The tutorial this follows: https://fastapi.tiangolo.com/tutorial/security/get-current-user/
The token "decoding" is a stub, so this step is not secure. It only shows the structure.
"""
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


def fake_decode_token(token: str) -> User:
    # A real implementation verifies a signature (see the JWT step of the lesson).
    return User(
        username=token + "fakedecoded", email="john@example.com", full_name="John Doe"
    )


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    # A dependency that depends on the security scheme: every route that needs the user
    # declares get_current_user and never touches the raw token.
    return fake_decode_token(token)


@app.get("/users/me")
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
