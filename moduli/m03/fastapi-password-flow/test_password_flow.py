"""Tests for the four steps of the password-flow tutorial."""
from fastapi.testclient import TestClient

import time
from datetime import timedelta

import jwt

import first_steps
import get_current_user
import oauth2_jwt
import simple_oauth2

step1 = TestClient(first_steps.app)
step2 = TestClient(get_current_user.app)
step3 = TestClient(simple_oauth2.app)
step4 = TestClient(oauth2_jwt.app)


def bearer(token: str) -> dict:
    """Build the Authorization header that carries a bearer token."""
    return {"Authorization": f"Bearer {token}"}


# Step 1: OAuth2PasswordBearer only extracts the token from the request ----------------

def test_step1_without_token_is_401():
    """A request with no Authorization header is rejected and told to use Bearer."""
    response = step1.get("/items/")
    assert response.status_code == 401
    # RFC 6750: a 401 must say which authentication scheme the client has to use.
    assert response.headers["www-authenticate"] == "Bearer"


def test_step1_hands_the_token_to_the_route():
    """The dependency passes the raw token string to the route, with no validation."""
    response = step1.get("/items/", headers=bearer("foobar"))
    assert response.json() == {"token": "foobar"}


def test_step1_declares_the_oauth2_scheme_in_openapi():
    """The generated OpenAPI document describes the password flow and its token URL.

    This is what makes the "Authorize" button appear in the interactive docs.
    """
    schemes = step1.get("/openapi.json").json()["components"]["securitySchemes"]
    flow = schemes["OAuth2PasswordBearer"]["flows"]["password"]
    assert schemes["OAuth2PasswordBearer"]["type"] == "oauth2"
    assert flow["tokenUrl"] == "token"


# Step 2: a dependency turns the token into a user -------------------------------------

def test_step2_returns_the_stub_user():
    """Any token is "decoded" by a fake function, so the route returns the stub user."""
    response = step2.get("/users/me", headers=bearer("abc"))
    assert response.status_code == 200
    assert response.json()["username"] == "abcfakedecoded"


def test_step2_without_token_is_401():
    """The user dependency reuses the step 1 scheme, so a missing token is still a 401."""
    assert step2.get("/users/me").status_code == 401


# Step 3: real login with form data, fake users and a username-as-token ----------------

def login(username: str, password: str):
    """Call the token endpoint the way OAuth2 requires."""
    # Form data, not JSON.
    return step3.post("/token", data={"username": username, "password": password})


def test_step3_login_returns_a_bearer_token():
    """A valid login returns the standard OAuth2 token response."""
    response = login("johndoe", "secret")
    assert response.status_code == 200
    assert response.json() == {"access_token": "johndoe", "token_type": "bearer"}


def test_step3_wrong_password_and_unknown_user_give_the_same_error():
    """Both failures return an identical response.

    The client cannot tell whether a username exists, which avoids user enumeration.
    """
    wrong = login("johndoe", "nope")
    unknown = login("nobody", "secret")
    assert wrong.status_code == unknown.status_code == 400
    assert wrong.json() == unknown.json() == {"detail": "Incorrect username or password"}


def test_step3_login_with_json_body_is_rejected():
    """The token endpoint accepts only form data, so a JSON body fails validation (422)."""
    response = step3.post("/token", json={"username": "johndoe", "password": "secret"})
    assert response.status_code == 422


def test_step3_full_flow_reads_the_current_user():
    """Log in, then use the returned token to read the profile of the logged-in user."""
    token = login("johndoe", "secret").json()["access_token"]
    response = step3.get("/users/me", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "johndoe"
    # The response model must not leak the stored password hash.
    assert "hashed_password" not in body


def test_step3_without_token_is_401_with_challenge():
    """No token: 401 plus the WWW-Authenticate challenge."""
    response = step3.get("/users/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_step3_unknown_token_is_401():
    """A token that maps to no user is treated as not authenticated."""
    response = step3.get("/users/me", headers=bearer("ghost"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_step3_disabled_user_is_400():
    """A valid login of a disabled account is accepted, but the protected route refuses it."""
    token = login("alice", "secret2").json()["access_token"]
    response = step3.get("/users/me", headers=bearer(token))
    assert response.status_code == 400
    assert response.json() == {"detail": "Inactive user"}


def test_step3_the_token_is_forgeable_by_design():
    """Documents a known weakness of this step: the token is just the username.

    Anybody who knows a username can build a valid token without logging in.
    This is the limit the next lesson step (password hashing and JWT) removes.
    """
    response = step3.get("/users/me", headers=bearer("johndoe"))
    assert response.status_code == 200


# Step 4: Argon2 password hashes and signed, expiring JWT tokens ------------------------

def login4(username: str, password: str):
    """Call the token endpoint of step 4."""
    return step4.post("/token", data={"username": username, "password": password})


def forge(claims: dict, key: str = oauth2_jwt.SECRET_KEY, algorithm: str = "HS256") -> str:
    """Sign arbitrary claims, to play the attacker or an old token."""
    return jwt.encode(claims, key, algorithm=algorithm)


def test_step4_login_returns_a_jwt_not_the_username():
    """The access token is a three-part JWT whose subject is the user, not the username itself."""
    body = login4("johndoe", "secret").json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] != "johndoe"
    assert body["access_token"].count(".") == 2
    claims = jwt.decode(body["access_token"], oauth2_jwt.SECRET_KEY, algorithms=["HS256"])
    assert claims["sub"] == "johndoe"
    assert "exp" in claims


def test_step4_token_expires_after_the_configured_minutes():
    """The exp claim is about ACCESS_TOKEN_EXPIRE_MINUTES after the login."""
    token = login4("johndoe", "secret").json()["access_token"]
    claims = jwt.decode(token, oauth2_jwt.SECRET_KEY, algorithms=["HS256"])
    lifetime = claims["exp"] - time.time()
    assert 0 < lifetime <= oauth2_jwt.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_step4_full_flow_reads_the_current_user():
    """Log in, then use the JWT to read the profile, without the password hash."""
    token = login4("johndoe", "secret").json()["access_token"]
    response = step4.get("/users/me/", headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["username"] == "johndoe"
    assert "hashed_password" not in response.json()


def test_step4_wrong_password_and_unknown_user_give_the_same_401():
    """Both failures return an identical 401 with the Bearer challenge."""
    wrong = login4("johndoe", "nope")
    unknown = login4("nobody", "secret")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Incorrect username or password"}
    assert wrong.headers["www-authenticate"] == "Bearer"


def test_step4_the_username_is_no_longer_a_valid_token():
    """The forgery documented in step 3 stops working: "johndoe" is not a signed JWT."""
    response = step4.get("/users/me/", headers=bearer("johndoe"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_step4_token_signed_with_another_key_is_rejected():
    """Without the secret key an attacker cannot mint a token, even with a valid subject."""
    token = forge({"sub": "johndoe"}, key="another-key-of-at-least-32-bytes-long")
    assert step4.get("/users/me/", headers=bearer(token)).status_code == 401


def test_step4_tampered_payload_is_rejected():
    """Changing the subject of a real token breaks its signature."""
    token = login4("johndoe", "secret").json()["access_token"]
    header, _, signature = token.split(".")
    evil = forge({"sub": "alice"}).split(".")[1]
    assert step4.get("/users/me/", headers=bearer(f"{header}.{evil}.{signature}")).status_code == 401


def test_step4_unsigned_token_with_alg_none_is_rejected():
    """The server only accepts HS256, so a token that declares alg none is refused."""
    unsigned = jwt.encode({"sub": "johndoe"}, key=None, algorithm="none")
    assert step4.get("/users/me/", headers=bearer(unsigned)).status_code == 401


def test_step4_expired_token_is_rejected():
    """A correctly signed token is refused once its exp has passed."""
    token = oauth2_jwt.create_access_token({"sub": "johndoe"}, timedelta(seconds=-1))
    assert step4.get("/users/me/", headers=bearer(token)).status_code == 401


def test_step4_token_without_subject_is_rejected():
    """A signed token with no sub claim identifies nobody."""
    token = oauth2_jwt.create_access_token({"name": "johndoe"}, timedelta(minutes=5))
    assert step4.get("/users/me/", headers=bearer(token)).status_code == 401


def test_step4_token_for_unknown_user_is_rejected():
    """A valid signature is not enough: the subject must still exist."""
    token = oauth2_jwt.create_access_token({"sub": "ghost"}, timedelta(minutes=5))
    assert step4.get("/users/me/", headers=bearer(token)).status_code == 401


def test_step4_disabled_user_is_400():
    """A disabled account can log in and get a token, but the protected route refuses it."""
    token = login4("alice", "secret2").json()["access_token"]
    response = step4.get("/users/me/", headers=bearer(token))
    assert response.status_code == 400
    assert response.json() == {"detail": "Inactive user"}


def test_step4_passwords_are_stored_as_argon2_hashes():
    """No stored value is a plain password, and the hash verifies only the right password."""
    stored = oauth2_jwt.fake_users_db["johndoe"]["hashed_password"]
    assert stored.startswith("$argon2")
    assert "secret" not in stored
    assert oauth2_jwt.verify_password("secret", stored)
    assert not oauth2_jwt.verify_password("secret2", stored)


def test_step4_same_password_hashes_differently_each_time():
    """The salt makes two hashes of one password differ, yet both verify."""
    first = oauth2_jwt.get_password_hash("secret")
    second = oauth2_jwt.get_password_hash("secret")
    assert first != second
    assert oauth2_jwt.verify_password("secret", first)
    assert oauth2_jwt.verify_password("secret", second)
