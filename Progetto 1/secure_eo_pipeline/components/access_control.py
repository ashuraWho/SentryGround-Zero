from secure_eo_pipeline import config  # For users and roles
from secure_eo_pipeline.utils.logger import audit_log  # For security events
from secure_eo_pipeline.db import sqlite_adapter

# =============================================================================
# Access Control Component (RBAC)
# =============================================================================
# ROLE IN ARCHITECTURE:
# This is the "Security Gateway". It sits between the User and the Data.
#
# MODEL: Role-Based Access Control (RBAC).
# - We do NOT assign permissions to people.
# - We assign permissions to ROLES.
# - We then assign ROLES to people.
#
# WHY THIS IS SECURE:
# This ensures "Consistency". If we update the 'Analyst' role, 1000 analysts 
# get the update immediately without manual error.
# =============================================================================

import bcrypt  # For password verification


class AccessController:
    
    """
    Enforces the security policies defined in config.py.
    Provides two distinct services: Authentication (Who are you?) and Authorization (What can you do?).
    """

    def __init__(self):
        # In-memory tracking of failed login attempts and lockouts.
        self._failed_attempts = {}
        self._locked_until = {}

    def _is_secure_mode(self):
        return getattr(config, "MODE", "DEMO").upper() == "SECURE"

    def _check_lockout(self, username):
        """
        Returns True if the account is currently locked.
        """
        if not self._is_secure_mode():
            return False

        import time

        locked_until = self._locked_until.get(username)
        if locked_until is None:
            return False
        if time.time() >= locked_until:
            # Lockout window expired
            self._locked_until.pop(username, None)
            self._failed_attempts.pop(username, None)
            return False
        return True

    def _register_failure(self, username):
        """
        Registers a failed login attempt and applies lockout in SECURE mode.
        """
        if not self._is_secure_mode():
            return

        import time

        max_failures = getattr(config, "MAX_FAILED_LOGINS", 5)
        lockout_seconds = getattr(config, "LOCKOUT_SECONDS", 60)

        self._failed_attempts[username] = self._failed_attempts.get(username, 0) + 1
        if self._failed_attempts[username] >= max_failures:
            self._locked_until[username] = time.time() + lockout_seconds
            audit_log.warning(
                f"[AUTH] LOCKOUT: User '{username}' temporarily locked after too many failed attempts."
            )

    def _reset_failure_counter(self, username):
        self._failed_attempts.pop(username, None)
        self._locked_until.pop(username, None)

    def _validate_password_policy(self, password: str) -> bool:
        """
        Simple password policy used when creating users.
        Enforced only in SECURE mode to keep the demo flexible.
        """
        if not self._is_secure_mode():
            return True

        if len(password) < 8:
            return False
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        return has_upper and has_lower and has_digit and has_special

    def authenticate(self, username, password):
        
        """
        Validates the identity of the user.
        
        ARGUMENTS:
            username (str): The identifier provided by the user.
            password (str): The secret password to verify.
            
        LOGIC:
        Checks the mock 'database' in config.py.
        - If user not found: Fail.
        - If password hash mismatch: Fail.
        - If verified: Return role.
        """
        
        # Step 0: Check for active lockout in SECURE mode
        if self._check_lockout(username):
            audit_log.warning(f"[AUTH] FAILURE: Login attempt while '{username}' is locked out.")
            return None

        # Step 1: Query the user database for the provided username
        if getattr(config, "USE_SQLITE", False):
            user_record = sqlite_adapter.get_user(username)
        else:
            user_record = config.USERS_DB.get(username)
        
        # Step 2: Treat missing users as authentication failures
        if not user_record:
            # Case A: User is unknown
            # RATIONALE: We use generic error messages in logs? No, logs should be specific.
            # User facing errors should be generic ("Invalid credentials") to prevent enumeration.
            audit_log.warning(f"[AUTH] FAILURE: Unknown user '{username}'.")
            self._register_failure(username)
            return None
            
        # Step 3: Verify the password against the stored bcrypt hash
        stored_hash = user_record.get("password_hash", user_record.get("hash")).encode('utf-8')
        role = user_record["role"]
        
        if role == "none" or user_record.get("disabled"):
            audit_log.warning(f"[AUTH] FAILURE: User '{username}' is disabled/banned.")
            self._register_failure(username)
            return None

        # Check password
        # bcrypt.checkpw requires bytes for both arguments
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            # Case B: Password matches. Log success.
            audit_log.info(f"[AUTH] SUCCESS: User '{username}' identified as '{role}'.")
            self._reset_failure_counter(username)
            return role
        else:
            # Case C: Password mismatch
            audit_log.warning(f"[AUTH] FAILURE: Invalid password for '{username}'.")
            self._register_failure(username)
            return None



    def authorize(self, username, action):
        
        """
        Validates if an authenticated user has the right to perform a specific action.
        
        ARGUMENTS:
            username (str): The identity to check.
            action (str): The operation (e.g., 'read', 'write', 'process', 'manage_keys').
            
        GOAL:
        Enforce the principle of "Least Privilege".
        """
        
        # NOTE: In a stateful session (like CLI), we usually don't re-authenticate with password
        # for every single action. We trust the 'current_role' stored in session (main.py).
        # However, for this specific class design, we need to look up the role from the username.
        
        # Lookup role directly from DB (simulating a session token check)
        if getattr(config, "USE_SQLITE", False):
            user_record = sqlite_adapter.get_user(username)
        else:
            user_record = config.USERS_DB.get(username)
        
        if not user_record:
            return False
            
        role_name = user_record["role"]
        
        # Step 3: Map the Role Name to its detailed definition in the config
        # This tells us exactly what permissions this role holds.
        role_def = config.ROLES.get(role_name)  # Looks up the role definition
        
        # Step 4: Safety check. If the role exists in USERS but not in ROLES (misconfiguration)
        if not role_def:
            # Log a system error
            audit_log.error(f"[ACCESS] CONFIG ERROR: Role '{role_name}' is not defined in the master policy.")  # Logs error if role is undefined
            return False
            
        # Step 5: Extract the list of allowed actions for this role
        # If the 'permissions' key is missing, default to an empty list (Secure Fail)
        permissions = role_def.get("permissions", [])  # Gets the permission list, defaulting to empty
        
        # Step 6: The Core Permission Check
        # Does the list of allowed permissions contain the requested action?
        if action in permissions:  # Checks if the action is allowed
            # ACCESS GRANTED
            # RATIONALE: Logging successful access creates a clear audit trail.
            audit_log.info(f"[ACCESS] GRANTED: {username} ({role_name}) is authorized for '{action}'.")  # Logs access granted and returns True
            return True
        else:
            # ACCESS DENIED
            # RATIONALE: This log is critical for detecting 'Privilege Escalation' attempts.
            audit_log.warning(f"[ACCESS] DENIED: {username} ({role_name}) missing required permission: '{action}'.")  # Logs access denied and returns False
            return False

    # -------------------------------------------------------------------------
    # User management helpers (backed by SQLite when enabled)
    # -------------------------------------------------------------------------

    def list_users(self):
        """
        Returns a list of user records suitable for display in the CLI.
        """
        if getattr(config, "USE_SQLITE", False):
            return sqlite_adapter.list_users()
        # Fallback to in-memory USERS_DB
        users = []
        for username, record in config.USERS_DB.items():
            users.append(
                {
                    "username": username,
                    "role": record["role"],
                    "disabled": record["role"] == "none",
                    "created_at": "N/A",
                }
            )
        return users

    def create_user(self, username, password, role):
        """
        Creates or updates a user with the given password and role.
        """
        if not self._validate_password_policy(password):
            raise ValueError(
                "Password does not meet minimum complexity requirements in SECURE mode "
                "(min 8 chars, upper, lower, digit, special)."
            )
        # Hash password using bcrypt
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

        if getattr(config, "USE_SQLITE", False):
            sqlite_adapter.create_user(username, password_hash, role)
        else:
            config.USERS_DB[username] = {"role": role, "hash": password_hash}

        audit_log.info(f"[IAM] User '{username}' created/updated with role '{role}'.")

    def delete_user(self, username):
        """
        Permanently deletes a user.
        """
        if getattr(config, "USE_SQLITE", False):
            sqlite_adapter.delete_user(username)
        else:
            config.USERS_DB.pop(username, None)

        audit_log.warning(f"[IAM] User '{username}' deleted from directory.")

    def update_role(self, username, role):
        """
        Updates the role associated with a user.
        """
        if getattr(config, "USE_SQLITE", False):
            sqlite_adapter.update_user_role(username, role)
        else:
            if username in config.USERS_DB:
                config.USERS_DB[username]["role"] = role

        audit_log.info(f"[IAM] Role for '{username}' updated to '{role}'.")

    def set_disabled(self, username, disabled=True):
        """
        Marks a user account as disabled/enabled.
        """
        if getattr(config, "USE_SQLITE", False):
            sqlite_adapter.disable_user(username, disabled)
        else:
            if username in config.USERS_DB:
                config.USERS_DB[username]["role"] = "none" if disabled else config.USERS_DB[
                    username
                ].get("role", "user")

        state = "disabled" if disabled else "enabled"
        audit_log.warning(f"[IAM] User '{username}' has been {state}.")
