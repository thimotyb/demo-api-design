"""Step 1 - First steps: declare an OAuth2 password-flow scheme and require a token.

Run:  uvicorn first_steps:app --reload      then open http://127.0.0.1:8000/docs

The tutorial this follows: https://fastapi.tiangolo.com/tutorial/security/first-steps/
Nothing here checks the token. The step only shows how FastAPI extracts it.
"""
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

# tokenUrl is where a client sends username and password to get a token. This line does not
# create that endpoint (step 3 does); it declares the URL, adds the scheme to the OpenAPI
# document and makes /docs show the Authorize button. The value is relative, so it keeps
# working behind a proxy.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/items/")
async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
    # The dependency reads the "Authorization: Bearer <token>" header and hands over <token>.
    # Without that header (or without the "Bearer" prefix) FastAPI answers 401 by itself.
    return {"token": token}
