def make_user_payload(username: str = "testuser", email: str = "test@example.com", password: str = "testpassword"):
    payload = {
        "username": username,
        "email": email,
        "password": password,
    }
    return payload