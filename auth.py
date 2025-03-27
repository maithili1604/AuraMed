from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import re
import requests
from flask import jsonify

class AuthHandler:
    def __init__(self, mongo):
        self.mongo = mongo

    def validate_password(self, password):
        """
        Validates if the password is strong based on the following criteria:
        - At least 8 characters.
        - Contains at least one uppercase letter.
        - Contains at least one lowercase letter.
        - Contains at least one number.
        - Contains at least one special character.
        - Does not contain spaces.
        """
        if len(password) < 8:
            return False
        if not re.search(r"[A-Z]", password):
            return False
        if not re.search(r"[a-z]", password):
            return False
        if not re.search(r"[0-9]", password):
            return False
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False
        if re.search(r"\s", password):
            return False
        return True

    def handle_login(self, request):
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            user = self.mongo.db.users.find_one({"email": email})

            if user and check_password_hash(user["password"], password):
                session["user_email"] = email
                session["user_id"] = str(user["_id"])
                return jsonify({"success": True, "redirect_url": url_for("home")})
            else:
                return jsonify({"success": False, "message": "Invalid credentials"})

        return render_template("login.html")

    def handle_signup(self, request):
        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")

            if not self.validate_password(password):
                return jsonify({
                    "success": False,
                    "message": "Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character."
                })

            if self.mongo.db.users.find_one({"email": email}):
                return jsonify({"success": False, "message": "Email already registered. Please log in."})

            hashed_password = generate_password_hash(password)
            user = {
                "name": name,
                "email": email,
                "password": hashed_password,
                "phone_number": "",
            }

            inserted_user = self.mongo.db.users.insert_one(user)

            session["user_email"] = email
            session["user_id"] = str(inserted_user.inserted_id)

            return jsonify({"success": True, "redirect_url": url_for("home")})

        return jsonify({"success": False, "message": "Invalid request method"})

    def get_google_provider_cfg(self, discovery_url):
        return requests.get(discovery_url).json()

    def handle_google_callback(self, client, request, discovery_url, client_id, client_secret):
        code = request.args.get("code")
        google_provider_cfg = self.get_google_provider_cfg(discovery_url)
        token_endpoint = google_provider_cfg["token_endpoint"]

        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url,
            redirect_url="https://auramed.onrender.com/login/google/callback",
            code=code,
        )
        token_response = requests.post(
            token_url, headers=headers, data=body, auth=(client_id, client_secret)
        )
        client.parse_request_body_response(token_response.text)

        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        user_info = userinfo_response.json()
        email = user_info["email"]
        name = user_info.get("name", "User")

        user = self.mongo.db.users.find_one({"email": email})
        if not user:
            user_id = self.mongo.db.users.insert_one({
                "name": name,
                "email": email,
                "password": None,
                "phone_number": "",
            }).inserted_id
        else:
            user_id = user["_id"]

        session["user_email"] = email
        session["user_id"] = str(user_id)
        return redirect(url_for("home"))
