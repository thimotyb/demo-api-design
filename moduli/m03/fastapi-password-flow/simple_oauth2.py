"""Step 3 - Simple OAuth2 with password and bearer: a /token endpoint and real checks.

Run:  uvicorn simple_oauth2:app --reload
Then in /docs press Authorize and log in as johndoe / secret.

The tutorial this follows: https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/

Teaching limits, kept on purpose so the structure stays visible:
- the "hash" is a prefix, not a hash;
- the access token is the username, so anybody can forge it.
The next lesson step replaces both with a password hash and a signed JWT.
"""
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}

app = FastAPI()


def fake_hash_password(password: str) -> str:
    return "fakehashed" + password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    # The stored model has the password hash; the public User model does not, so the hash
    # can never leak through a response.
    hashed_password: str


def get_user(db: dict, username: str) -> UserInDB | None:
    if username in db:
        return UserInDB(**db[username])
    return None


def fake_decode_token(token: str) -> UserInDB | None:
    # This provides no security at all: the token is just the username.
    return get_user(fake_users_db, token)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = fake_decode_token(token)
    if not user:
        # 401 for a missing or unknown credential. The WWW-Authenticate header is part of
        # the bearer-token specification for any 401.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    # A second dependency on top of the first: authenticated is not enough, the account
    # must also be enabled.
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # OAuth2PasswordRequestForm reads form data (not JSON): username, password and the
    # optional scope, grant_type, client_id, client_secret. This is why python-multipart
    # must be installed.
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    user = UserInDB(**user_dict)
    if fake_hash_password(form_data.password) != user.hashed_password:
        # Same message for an unknown user and a wrong password.
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    # The response keys are fixed by the OAuth2 specification.
    return {"access_token": user.username, "token_type": "bearer"}


# The tutorial omits response_model, and then the whole UserInDB, hash included, is returned.
# response_model=User filters the response down to the public fields.
@app.get("/users/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    # The object is a UserInDB; response_model drops hashed_password from the response.
    return current_user
