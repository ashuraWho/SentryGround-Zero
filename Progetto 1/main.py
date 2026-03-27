import os  # The program can check and build file paths and directories
import time  # To pause execution for user feedback and simulation timing
import random  # To generate non-deterministic product identifiers.

# Import components from the Rich library to build a modern terminal user interface
from rich.console import Console  # To handle styled terminal output
from rich.panel import Panel  # To draw boxed UI elements
from rich.table import Table  # To format tabular output
from rich import box  # For table border styles
from rich.prompt import Prompt  # To collect interactive input
from rich.progress import track  # For hacker-style progress bars

from secure_eo_pipeline import config  # For shared settings like directories and users
from secure_eo_pipeline.components.data_source import EOSimulator  # To generate synthetic products
from secure_eo_pipeline.components.ingestion import IngestionManager  # For validation and hashing
from secure_eo_pipeline.components.processing import ProcessingEngine  # To apply QC and calibration
from secure_eo_pipeline.components.storage import ArchiveManager  # To encrypt and store products
from secure_eo_pipeline.components.access_control import AccessController  # For authentication and authorization
from secure_eo_pipeline.resilience.backup_system import ResilienceManager  # To back up and restore files
from secure_eo_pipeline.resilience.backup_system import ResilienceManager  # To back up and restore files
from secure_eo_pipeline.utils import security  # For hashing in recovery logic
from secure_eo_pipeline.components.ids import IntrusionDetectionSystem # For log analysis
from secure_eo_pipeline.db import sqlite_adapter

# Create a global Rich Console for all printing operations
console = Console()

class InteractiveSession:
    
    """
    Controller class that manages the state and command loop of the CLI application.
    """
    
    def __init__(self):  # Define the constructor
        
        """
        Initializes the session state and instantiates all system components.
        """
        
        # --- SESSION STATE ---
        self.current_user = None   # Stores the username of the logged-in operator -> None represents no logged-in user
        self.current_role = None   # Stores the RBAC role (admin/analyst/user) -> None represents no active role
        self.active_product = None   # Stores the ID of the product currently being processed -> None represents no current product
        
        # --- COMPONENT INSTANTIATION ---
        self.source = EOSimulator()  # Creates a simulator instance to generate raw data
        self.ingestion_manager = IngestionManager()  # Creates an ingestion manager to validate and fingerprint data
        self.processor = ProcessingEngine()  # Creates a processing engine to perform QC and calibration
        self.archive_manager = ArchiveManager()  # Creates an archive manager to encrypt and store data
        self.ac = AccessController()  # Creates an access controller for RBAC checks (Role-Based Access Control)
        self.ac = AccessController()  # Creates an access controller for RBAC checks (Role-Based Access Control)
        self.backup = ResilienceManager()  # Creates a resilience manager for backup and recovery
        self.ids = IntrusionDetectionSystem()  # Creates an intrusion detection system for log analysis
        
        # --- PIPELINE TRACKING ---
        # This dictionary tracks the completion status of each lifecycle stage
        self.state = {
            "generated": False,  # Step 1: Raw data created -> False indicates no raw data yet
            "ingested": False,   # Step 2: Validated and fingerprinted -> False indicates ingestion not done
            "processed": False,  # Step 3: Calibrated and QC checked -> False indicats processing not done
            "archived": False,   # Step 4: Encrypted and vaulted -> False indicates archiving not done
            "hacked": False      # Simulation status: Data corrupted on disk -> False indicates no corruption simulated
        }



    def clear(self):
        
        """
        Refreshes the terminal screen and repaints the application header.
        """
        
        # Standard Rich clear command
        console.clear()
        # Repaint the top banner
        self.print_banner()



    def print_banner(self):  # To show title and status
        
        """
        Displays the main application branding and real-time session status.
        """
        
        # Render the main project title in a cyan panel
        console.print(Panel(
            "[bold cyan]SECURE EARTH OBSERVATION PIPELINE[/bold cyan]\n"  # The main title of the application, styled in bold cyan
            "[italic white]Interactive Operator Console (V1.0)[/italic white]",  # Subtitle in italic white
            border_style="cyan",  # Sets the panel border color
            expand=False  # Prevents the panel from expanding to full width
        ))
        
        # --- DYNAMIC STATUS BAR ---
        # Format the user display based on login status
        user_display = f"[green]{self.current_user}[/green]" if self.current_user else "[red]Not Logged In[/red]"  # To show logged-in user or not
        role_display = f"({self.current_role})" if self.current_role else ""  # To show the current role if available
        
        # Format the product display
        product_display = f"[blue]{self.active_product}[/blue]" if self.active_product else "[dim]None[/dim]"  # To show the active product or none if not set
        
        # Create an invisible grid for aligned layout
        grid = Table.grid(expand=True)  # Creates a grid table to align status text
        grid.add_column()  # Column for User info
        grid.add_column(justify="right")  # Column for Product info
        
        # Add the status row to the grid
        grid.add_row(  # Adds a row with user and product status text
            f"User: {user_display} {role_display}",  # First cell shows user and role
            f"Active Target: {product_display}"  # Second cell shows the active product
        )
        
        # Wrap the grid in a dim white panel for visual separation
        console.print(Panel(grid, style="dim white"))



    def help_menu(self):
        
        """
        Prints the command reference table for the operator.
        """
        
        # Create a table to organize commands and descriptions
        table = Table(title="\nAvailable Operator Commands\n", box=None)
        
        # Define the header columns
        table.add_column("Command", style="bold cyan")
        table.add_column("Description", style="white")
        
        # Core pipeline
        table.add_row("[bold underline]Core pipeline[/bold underline]", "")
        table.add_row("login", "Authenticate as an operator")
        table.add_row("logout", "End the current session")
        table.add_row("scan", "Generate a new synthetic product")
        table.add_row("ingest", "Validate and fingerprint raw data")
        table.add_row("process", "Run calibration and QC checks")
        table.add_row("archive", "Encrypt and store the product")
        table.add_row("recover", "Verify archive integrity and restore from backup")
        table.add_row("status", "Show lifecycle state for the active product")
        table.add_row("", "")

        # Security operations
        table.add_row("[bold underline]Security operations[/bold underline]", "")
        table.add_row("hack", "Simulate corruption of the encrypted archive")
        table.add_row("ids", "Run intrusion detection on audit data")
        table.add_row("rotate_keys", "Rotate cryptographic keys (admin only)")
        table.add_row("health", "Run basic health checks on config, DB, and directories")
        table.add_row("", "")

        # Attack scenarios (demo)
        table.add_row("[bold underline]Attack scenarios[/bold underline]", "")
        table.add_row("bruteforce_login", "Simulate a brute-force login attack")
        table.add_row("tamper_metadata", "Simulate metadata tampering")
        table.add_row("delete_backup", "Simulate backup sabotage")
        table.add_row("full_attack", "Run the full multi-step attack narrative")
        table.add_row("", "")

        # User and IAM management
        table.add_row("[bold underline]User & IAM (admin)[/bold underline]", "")
        table.add_row("add", "Create or update a user account")
        table.add_row("list", "List all user accounts")
        table.add_row("remove", "Delete a user account")
        table.add_row("change_role", "Change a user's role")
        table.add_row("disable", "Disable or re-enable a user account")
        table.add_row("", "")

        # Utility
        table.add_row("[bold underline]Utility[/bold underline]", "")
        table.add_row("help", "Show this command list")
        table.add_row("exit", "Close the console")
        
        # Output the table to the console
        console.print(table)



    def print_status_panel(self): # To show pipeline state
        
        """
        Displays a visual checklist of the product's progress through the pipeline.
        """
        
        # Create a simple status table
        table = Table(box=None)
        table.add_column("Lifecycle Stage")  # Adds the Lifecycle Stage column
        table.add_column("Status")  # Adds the Status column
        
        # Iterate through defined stages
        stages = ["generated", "ingested", "processed", "archived", "hacked"]  # Defines the ordered list of stages
        for s in stages:  # Starts the loop over stages
            # Determine the status label based on the state dictionary
            status = "[green]COMPLETED[/green]" if self.state[s] else "[dim]PENDING[/dim]"  # Sets status text based on completion
            
            # Special formatting for the 'Hacked' status (Red indicates danger)
            if s == "hacked" and self.state[s]:  # Checks if the hacked stage is true
                status = "[bold red]CORRUPTED[/bold red]"  # Overrides status to red corrupted text
                
            # Add the row to the table
            table.add_row(s.upper(), status)
            
        # Wrap the table in a panel for the final UI
        console.print(Panel(table, title="Product Verification Status"))  # Prints the table inside a titled panel



    def login(self):  # To authenticate a user
        
        """
        Authenticates an operator using the Access Control component.
        """
        
        # In SECURE mode we avoid enumerating concrete account names to reduce
        # the risk of username disclosure. In DEMO mode we show them to help
        # the learner.
        console.print("\n[bold underline]Mission Personnel Directory:[/bold underline]")
        if config.MODE == "DEMO":
            # Display known users to assist the simulation operator
            if getattr(config, "USE_SQLITE", False):
                users = sqlite_adapter.list_users()
                for u in users:
                    status = "[red]DISABLED[/red]" if u["disabled"] else "[green]ACTIVE[/green]"
                    console.print(f" - {u['username']} ({u['role']}) {status}")
            else:
                for u, record in config.USERS_DB.items():
                    role = record["role"]
                    status = "[green]ACTIVE[/green]"
                    console.print(f" - {u} ({role}) {status}")
        else:
            console.print("[dim]User list is hidden in SECURE mode. Please enter your assigned username.[/dim]")
            
        # Capture user input
        user = Prompt.ask("\nEnter Username")
        
        # Capture password securely (hidden input)
        # We use Console.input with password=True from Rich, or getpass
        password = console.input("[bold]Enter Password:[/bold] ", password=True)
        
        # Call the Access Controller to verify credentials and retrieve role
        role = self.ac.authenticate(user, password)
        
        if role:  # Checks if authentication succeeded
            # Update the session state upon success
            self.current_user = user  # Stores the username as the active user
            self.current_role = role  # Stores the role as the active role
            console.print(f"[green]✅ Access Granted. Welcome, Operator {user}.[/green]")  # Prints an access granted message
        else:  # Else branch for failure
            # Report failure
            console.print("[red]❌ Access Denied. Identity not recognized or password incorrect.[/red]")  # Prints an access denied message



    def check_auth(self, action):  # To enforce RBAC
        
        """
        Validates if the current operator is authorized to perform a specific action.
        
        RETURNS:
            bool: True if authorized, False otherwise.
        """
        
        # Step 1: Check if anyone is even logged in
        if not self.current_user:  # Checks if a user is logged in
            console.print("[red]❌ Error: Authentication Required. Please 'login'.[/red]")  # Prints an error when no user is logged in
            return False  # Returns False to block the action
            
        # Step 2: Query the Access Controller for granular permission check
        if self.ac.authorize(self.current_user, action):  # Calls authorize to check permission for the action
            # Permission granted
            return True
        else:
            # Permission denied based on RBAC policy
            console.print(f"[red]❌ Error: Unauthorized. '{self.current_user}' lacks '{action}' rights.[/red]")  # Prints a detailed unauthorized message
            return False



    def check_prereq(self, prereq_key, step_name):  # To enforce pipeline order
        
        """
        Enforces the linear flow of the data pipeline.
        Ensures users don't try to archive data that hasn't been processed yet.
        """
        
        # Step 1: Ensure we have a product to work on
        if not self.active_product:  # Checks if a product is active
             console.print("[yellow]⚠️ Warning: No active target selected. Run 'scan' first.[/yellow]")  # Prints warning if no product was generated
             return False  # Returns False to stop the command
        
        # Step 2: Ensure the preceding step was completed successfully
        if prereq_key and not self.state[prereq_key]:  # Checks the required stage status
             console.print(f"[yellow]⚠️ Warning: Cannot {step_name}. Prerequisites not met.[/yellow]")  # Prints warning if prerequisites are not met
             return False  # Returns False to stop the command
        
        return True  # Returns True if all prerequisites are satisfied



    def scan(self):  # To generate a new product
        
        """
        COMMAND: scan
        Generates a new raw satellite product (Level-0).
        """
        
        # Allow scanning without auth for the demo, but show a note
        if not self.current_user:  # Checks if no user is logged in
             console.print("[italic]Operating in Anonymous Mode...[/italic]")  # Prints a note that the session is anonymous
        
        # Create a semi-random ID to simulate a mission product name
        pid = f"Sentinel_2_{random.randint(1000,9999)}_Orbit{random.randint(10,99)}"  # Builds a randomized product ID string
        
        # Display a high-tech loading spinner
        # with console.status("[cyan]Acquiring Satellite Downlink (X-Band)...[/cyan]", spinner="earth"):  # Starts a Rich status spinner context
        #     time.sleep(2) # Simulate the duration of a signal pass -> Sleeps to simulate a satellite pass
        #     # Call the Simulator component to create files on disk
        #     self.source.generate_product(pid)

        # UI Upgrade: Hacker-style progress bar
        # Note: `track` only supports an iterable and optional description; for
        # spinners we would need a different Rich primitive. Here we keep a
        # simple progress bar for clarity and compatibility.
        for _ in track(range(20), description="[cyan]Acquiring Satellite Downlink (X-Band)...[/cyan]"):
            time.sleep(2)  # 2 seconds total
        self.source.generate_product(pid)
        
        # Update session state
        self.active_product = pid  # Sets the active product ID
        self.state = {
            "generated": True,
            "ingested": False,
            "processed": False,
            "archived": False,
            "hacked": False
        }
        
        # Report success
        console.print(f"[green]✅ Signal Locked.[/green] New Target: [bold]{pid}[/bold]")  # Prints success and the product ID
        console.print("[dim italic]ℹ️  Metadata validated and Level-0 binary generated.[/dim italic]")  # Prints a short descriptive note



    def ingest(self):  # To validate and hash data
        
        """
        COMMAND: ingest
        Validates the raw data and creates the initial integrity hash.
        """
        
        # Step 1: Check if user has permission to 'process' data
        if not self.check_auth("process"): return  # Returns early if authorization fails
        
        # Step 2: Check if data was even generated
        if not self.check_prereq("generated", "Ingest"): return  # Returns early if data was not generated
        
        console.print("[dim italic]ℹ️  Validating schema and baselining SHA-256 integrity...[/dim italic]")  # Prints a message describing ingestion activity
        
        with console.status("[cyan]Performing Secure Ingestion...[/cyan]"):  # Starts a Rich status spinner context
            # Call the Ingestion component logic
            path = self.ingestion_manager.ingest_product(self.active_product)  # Calls the ingestion manager and captures the path
        
        if path:  # Checks if a valid path was returned
            # Success: Mark state
            self.state["ingested"] = True  # Marks the ingested stage as complete
            console.print("[green]✅ Ingestion successful.[/green] Data fingerprinted and staged.")  # Prints success message
        else:  # Else branch for failure
            console.print("[red]❌ Ingestion failed validation.[/red]")  # Prints failure message



    def process(self):  # To calibrate and QC data
        
        """
        COMMAND: process
        Converts raw data to scientific products and checks quality.
        """
        
        # Step 1: Authorization
        if not self.check_auth("process"): return  # Returns early if permission is missing
        
        # Step 2: Pipeline Order
        if not self.check_prereq("ingested", "Process"): return  # Returns early if ingestion is incomplete
        
        console.print("[dim italic]ℹ️  Applying radiometric calibration and checking for sensor noise...[/dim italic]")  # Prints processing explanation
        console.print("[dim italic]ℹ️  Applying radiometric calibration and checking for sensor noise...[/dim italic]")  # Prints processing explanation
        # with console.status("[cyan]Calibrating Radiometric Sensors (Level-0 -> Level-1)...[/cyan]", spinner="dots"):  # Starts a Rich status spinner context
        #     time.sleep(1.5) # Simulate computation time
        #     # Call the Processing component
        #     path = self.processor.process_product(self.active_product)  # Calls the processing engine and captures the path

        # UI Upgrade: Progress bar
        for _ in track(range(15), description="[magenta]Calibrating Radiometric Sensors (Level-0 -> Level-1)...[/magenta]"):
            time.sleep(1.5)
        path = self.processor.process_product(self.active_product)
            
        if path:  # Checks if processing returned a valid path
            # Success
            self.state["processed"] = True  # Marks the processed stage as complete
            console.print("[green]✅ Processing successful.[/green] Level-1C product ready.")  # Prints success message
        else:
            # Failure
            console.print("[red]❌ Processing failed Quality Control check.[/red]")  # Prints failure message



    def archive(self):  # To encrypt and store data
        
        """
        COMMAND: archive
        Encrypts the product and stores it in the high-security vault.
        """
        
        # Step 1: Authorization (Requires 'write' permission)
        if not self.check_auth("write"): return  # Returns early if permission is missing
        
        # Step 2: Pipeline Order
        if not self.check_prereq("processed", "Archive"): return  # Returns early if processing is incomplete
        
        console.print("[dim italic]ℹ️  Executing Fernet encryption and replicating to backup...[/dim italic]")  # Prints archiving explanation
        with console.status("[cyan]Vaulting Product...[/cyan]", spinner="dots"):  # Starts a Rich status spinner context
            time.sleep(1.5)  # Sleeps to simulate archiving time
            
            # 1. Move to Encrypted Archive
            self.archive_manager.archive_product(self.active_product)  # Calls archive_product to encrypt and store the product
            
            # 2. Immediately create a redundant backup for resilience
            self.backup.create_backup(self.active_product)  # Calls create_backup to replicate the encrypted file
            
        # Update state
        self.state["archived"] = True  # Marks the archived stage as complete
        console.print("[green]✅ Archiving successful.[/green] Data is encrypted-at-rest.")  # Prints success message


    # ---------------------------------------------------------------------
    # User management commands (Admin-only, backed by AccessController)
    # ---------------------------------------------------------------------

    def user_add(self):
        
        """
        COMMAND: user_add
        Creates or updates a user account (Admin only).
        """
        
        if not self.check_auth("manage_keys"):
            return

        username = Prompt.ask("Enter new username")
        role = Prompt.ask("Assign role", choices=list(config.ROLES.keys()))
        password = console.input("[bold]Enter Password for user:[/bold] ", password=True)

        self.ac.create_user(username, password, role)
        console.print(f"[green]✅ User '{username}' created/updated with role '{role}'.[/green]")

    def user_list(self):
        
        """
        COMMAND: user_list
        Lists all user accounts (Admin only).
        """
        
        if not self.check_auth("manage_keys"):
            return

        users = self.ac.list_users()

        table = Table(title="User Directory", box=None)
        table.add_column("Username", style="bold cyan")
        table.add_column("Role", style="white")
        table.add_column("Status", style="white")
        table.add_column("Created At", style="dim")

        for u in users:
            status = "[red]DISABLED[/red]" if u["disabled"] else "[green]ACTIVE[/green]"
            table.add_row(u["username"], u["role"], status, u.get("created_at", "N/A"))

        console.print(table)

    def user_remove(self):
        
        """
        COMMAND: user_remove
        Deletes a user account (Admin only).
        """
        
        if not self.check_auth("manage_keys"):
            return

        username = Prompt.ask("Enter username to delete")
        confirm = Prompt.ask(f"Are you sure you want to delete '{username}'? (yes/no)", choices=["yes", "no"], default="no")
        if confirm == "no":
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

        self.ac.delete_user(username)
        console.print(f"[green]✅ User '{username}' deleted.[/green]")

    def user_change_role(self):
        
        """
        COMMAND: user_change_role
        Changes the role assigned to a user (Admin only).
        """
        
        if not self.check_auth("manage_keys"):
            return

        username = Prompt.ask("Enter username to modify")
        role = Prompt.ask("New role", choices=list(config.ROLES.keys()))
        self.ac.update_role(username, role)
        console.print(f"[green]✅ User '{username}' role updated to '{role}'.[/green]")

    def user_disable(self):
        
        """
        COMMAND: user_disable
        Disables or enables a user account (Admin only).
        """
        
        if not self.check_auth("manage_keys"):
            return

        username = Prompt.ask("Enter username to modify")
        action = Prompt.ask("Choose action", choices=["disable", "enable"], default="disable")
        disabled = action == "disable"
        self.ac.set_disabled(username, disabled)
        state_label = "disabled" if disabled else "enabled"
        console.print(f"[green]✅ User '{username}' {state_label}.[/green]")



    def hack(self):  # To simulate corruption
        
        """
        COMMAND: hack
        Simulates an external attack that corrupts data on the storage disk.
        """
        
        # Verify there is actually an archived product to attack
        if not self.active_product or not self.state["archived"]:  # Checks for an archived active product
            console.print("[yellow]⚠️ Error: No archived data found to simulate an attack upon.[/yellow]")  # Prints warning if no archived product exists
            return  # Returns early to avoid errors
            
        console.print("[bold red]☠️ INITIATING SIMULATED DATA CORRUPTION SCENARIO...[/bold red]")  # Prints a dramatic warning message
        console.print("[dim]Step 1: Attacker gains unauthorized filesystem access to the secure archive.[/dim]")
        console.print("[dim]Step 2: Attacker locates the encrypted product and overwrites it with garbage.[/dim]")
        
        # Determine the physical path of the vaulted file
        target = os.path.join(config.ARCHIVE_DIR, f"{self.active_product}.enc")  # Constructs the encrypted file path
        
        if os.path.exists(target):  # Checks if the archive file exists
            # MALICIOUS ACTION: Overwrite the encrypted bytes with garbage text
            with open(target, "wb") as f:  # Opens the file for binary writing
                f.write(b"MALICIOUS_CORRUPTION_EVENT_000")  # Overwrites the file with garbage bytes
                
            # Update state to reflect corruption
            self.state["hacked"] = True  # Marks the hacked stage as true
            console.print(f"[red]✅ Attack successful.[/red] Primary data file has been corrupted.")  # Prints attack success message
        else:  # Else branch for missing file
            console.print("[red]❌ Attack failed: File not located.[/red]")  # Prints failure message for missing file


    def scenario_bruteforce_login(self):
        
        """
        COMMAND: scenario_bruteforce_login
        Simulates a brute-force attack with repeated failed logins by a malicious actor.
        """
        
        console.print("[bold red]⚠️ SCENARIO: Brute-Force Login Attack[/bold red]")
        console.print("[dim]An external attacker repeatedly guesses passwords for a high-value account.[/dim]")

        target_user = Prompt.ask("Target username for brute-force (default: hacker)", default="hacker")
        attempts = 5

        for i in range(1, attempts + 1):
            console.print(f"[dim]Attempt {i}/{attempts} with wrong password...[/dim]")
            # Always supply an incorrect password
            self.ac.authenticate(target_user, "wrong_password!")
            time.sleep(0.3)

        console.print("[yellow]Brute-force simulation complete. Run 'ids' to see detection results.[/yellow]")


    def scenario_tamper_metadata(self):
        
        """
        COMMAND: scenario_tamper_metadata
        Simulates an attacker modifying product metadata without touching the binary data.
        """
        
        if not self.active_product or not self.state["processed"]:
            console.print("[yellow]⚠️ Error: You need a processed product to tamper with. Run 'scan', 'ingest', 'process' first.[/yellow]")
            return

        console.print("[bold red]⚠️ SCENARIO: Metadata Tampering[/bold red]")
        console.print("[dim]An insider modifies product metadata to hide anomalies or fake provenance.[/dim]")

        meta_path = os.path.join(config.PROCESSING_DIR, f"{self.active_product}.json")
        if not os.path.exists(meta_path):
            console.print("[red]❌ Cannot find metadata file to tamper with.[/red]")
            return

        # Perform a subtle but detectable tampering: override qc_status and hash fields
        try:
            import json

            with open(meta_path, "r") as f:
                meta = json.load(f)

            meta["qc_status"] = "FORCED_OK"
            meta["tampered_flag"] = True
            if "original_hash" in meta:
                meta["original_hash"] = "0000TAMPERED0000"

            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=4)

            console.print("[red]✅ Metadata tampered.[/red] Run 'process' or 'archive' again to see integrity checks react.")
        except Exception as e:
            console.print(f"[red]❌ Failed to tamper metadata: {e}[/red]")


    def scenario_delete_backup(self):
        
        """
        COMMAND: scenario_delete_backup
        Simulates an attacker sabotaging the backup copy to break resilience.
        """
        
        if not self.active_product or not self.state["archived"]:
            console.print("[yellow]⚠️ Error: You need an archived product with backup. Run 'archive' first.[/yellow]")
            return

        console.print("[bold red]⚠️ SCENARIO: Backup Sabotage[/bold red]")
        console.print("[dim]An attacker with elevated privileges deletes the backup copy to prevent recovery.[/dim]")

        backup_path = os.path.join(config.BACKUP_DIR, f"{self.active_product}.enc")
        if not os.path.exists(backup_path):
            console.print("[yellow]Backup file not found. Perhaps it was never created or already removed.[/yellow]")
            return

        try:
            os.remove(backup_path)
            console.print("[red]✅ Backup deleted. System resilience has been weakened.[/red]")
        except Exception as e:
            console.print(f"[red]❌ Failed to delete backup: {e}[/red]")


    def scenario_full_attack(self):
        
        """
        COMMAND: scenario_full_attack
        Runs a full multi-step attack narrative:
        1) Brute-force attempts against an account.
        2) Insider-style metadata tampering on a processed product.
        3) Backup sabotage on an archived product.
        4) Direct corruption of the archive (hack).
        5) Intrusion detection scan (ids).
        """
        
        console.print("[bold red]☠️ SCENARIO: FULL ATTACK KILL CHAIN[/bold red]")
        console.print("[dim]This guided scenario chains together multiple attack techniques and then runs IDS.[/dim]")

        # Ensure we have a product going through the pipeline
        if not self.active_product or not self.state["generated"]:
            console.print("[cyan]No active product found. Generating one via 'scan'...[/cyan]")
            self.scan()

        # Require authentication for protected steps
        if not self.current_user:
            console.print("[yellow]You must be logged in to continue. Please authenticate as an analyst or admin.[/yellow]")
            self.login()
            if not self.current_user:
                console.print("[red]Aborting full attack scenario: authentication failed.[/red]")
                return

        # Step 1: Ingestion and processing (if not already done)
        if not self.state["ingested"]:
            console.print("[cyan]Step 1: Secure ingestion of the new product.[/cyan]")
            self.ingest()

        if not self.state["processed"]:
            console.print("[cyan]Step 2: Scientific processing and QC.[/cyan]")
            self.process()

        # Step 3: Archive and backup
        if not self.state["archived"]:
            console.print("[cyan]Step 3: Secure archiving and backup creation.[/cyan]")
            self.archive()

        # Step 4: Brute-force attempts against a high-value account
        console.print("[cyan]Step 4: Simulating external brute-force attempts against 'admin'.[/cyan]")
        target_user = "admin"
        for i in range(1, 4):
            console.print(f"[dim]Brute-force attempt {i}/3 on '{target_user}'...[/dim]")
            self.ac.authenticate(target_user, "wrong_password!")
            time.sleep(0.2)

        # Step 5: Insider-style metadata tampering
        console.print("[cyan]Step 5: Insider tampers with processing metadata.[/cyan]")
        self.scenario_tamper_metadata()

        # Step 6: Backup sabotage
        console.print("[cyan]Step 6: Attacker deletes the backup to weaken resilience.[/cyan]")
        self.scenario_delete_backup()

        # Step 7: Direct archive corruption
        console.print("[cyan]Step 7: Attacker corrupts the encrypted archive file.[/cyan]")
        self.hack()

        # Step 8: Intrusion detection
        console.print("[cyan]Step 8: Running IDS over accumulated logs and DB events.[/cyan]")
        self.run_ids()

        console.print("[green]✅ Full attack scenario completed. Review IDS output and audit logs for details.[/green]")



    def recover(self):  # To restore corrupted data
        
        """
        COMMAND: recover
        Uses resilience mechanisms to detect and repair the corruption.
        """
        
        # Requires high-level 'manage_keys' permission (Admin only)
        if not self.check_auth("manage_keys"): return  # Returns early if user is not authorized
        
        # Must be an archived product
        if not self.check_prereq("archived", "Recover"): return  # Returns early if archiving not completed
        
        console.print("[dim italic]ℹ️  Auditing storage integrity against secondary backup...[/dim italic]")  # Prints recovery explanation
        
        
        # Define a callback to fetch the "Known Good Hash" from the backup vault
        def get_expected_hash(p):  # Defines a nested function to retrieve the backup hash
            bk_path = os.path.join(config.BACKUP_DIR, f"{p}.enc")  # Builds the backup file path
            # Calculate the hash of the backup (trusted copy)
            return security.calculate_hash(bk_path)  # Returns the hash of the backup file

        with console.status("[green]Healing System...[/green]", spinner="material"):  # Starts a Rich status spinner context
            time.sleep(2) # Simulate audit and data transfer time
            # Trigger the Resilience Manager's recovery logic
            fixed = self.backup.verify_and_restore(self.active_product, get_expected_hash)  # Calls verify_and_restore and stores result
            
        if fixed:  # Checks if recovery succeeded
            # Success: Corruption repaired
            self.state["hacked"] = False  # Clears the hacked flag
            console.print("[green]✅ Recovery successful.[/green] System integrity restored.")  # Prints success message
        else:
             # Failure: Could not recover
             console.print("[red]❌ Recovery failed. Backup may also be compromised.[/red]")  # Prints failure message
             
             
             
    def rotate_keys(self):
        """
        COMMAND: rotate_keys
        Performs a full cryptographic key rotation.
        """
        # Requires high-level 'manage_keys' permission (Admin only)
        if not self.check_auth("manage_keys"): return

        console.print("[bold red]⚠️  WARNING: KEY ROTATION INITIATED.[/bold red]")
        console.print("[dim]This will re-encrypt the entire valid archive with a new key.[/dim]")
        
        confirm = Prompt.ask("Are you sure? (yes/no)", choices=["yes", "no"], default="no")
        if confirm == "no":
            console.print("[yellow]Key rotation cancelled.[/yellow]")
            return

        with console.status("[bold red]ROTATING SYSTEM KEYS...[/bold red]", spinner="bouncingBall"):
             success = security.rotate_keys(config.ARCHIVE_DIR, config.BACKUP_DIR)

        if success:
             console.print("[green]✅ Key Rotation Complete.[/green] New key is active.")
        else:
             console.print("[red]❌ Key Rotation Failed.[/red] See logs for details.")


    def run_ids(self):
        """
        COMMAND: ids
        Scans audit logs for security incidents.
        """
        # Authorization: Analyst or Admin
        if not self.check_auth("process") and not self.check_auth("manage_keys"): 
            return

        with console.status("[bold red]SCANNING AUDIT LOGS FOR THREATS...[/bold red]", spinner="bouncingBall"):
            time.sleep(2)
            incidents = self.ids.analyze_audit_log()

        if not incidents:
            console.print("[green]✅ System Secure. No threats detected.[/green]")
            return

        # Display Report
        console.print(f"\n[bold red]🚨 THREATS DETECTED: {len(incidents)}[/bold red]")
        
        table = Table(title="Intrusion Detection Report", box=box.HEAVY_EDGE)
        table.add_column("Severity", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Details", style="white")

        for inc in incidents:
            sev_style = "red" if inc["severity"] == "CRITICAL" else "yellow" if inc["severity"] == "HIGH" else "blue"
            table.add_row(
                f"[{sev_style}]{inc['severity']}[/{sev_style}]",
                inc["type"],
                inc["details"]
            )
        
        console.print(table)
        console.print("[dim]Recommended Action: Review audit.log and rotate keys if necessary.[/dim]\n")


    def health(self):
        
        """
        COMMAND: health
        Runs basic health checks on configuration, database and filesystem layout.
        """
        
        table = Table(title="System Health Check", box=None)
        table.add_column("Component", style="bold cyan")
        table.add_column("Status", style="white")
        table.add_column("Details", style="dim")

        # Config / mode
        table.add_row(
            "MODE",
            f"[green]{config.MODE}[/green]",
            "Operating mode (DEMO/SECURE) loaded from config/environment.",
        )

        # Directories
        for label, path in [
            ("INGEST_DIR", config.INGEST_DIR),
            ("PROCESSING_DIR", config.PROCESSING_DIR),
            ("ARCHIVE_DIR", config.ARCHIVE_DIR),
            ("BACKUP_DIR", config.BACKUP_DIR),
        ]:
            exists = os.path.isdir(path)
            status = "[green]OK[/green]" if exists else "[yellow]MISSING[/yellow]"
            table.add_row(label, status, path)

        # SQLite
        if getattr(config, "USE_SQLITE", False):
            try:
                conn = sqlite_adapter.get_connection()
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                users_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM audit_events")
                events_count = cur.fetchone()[0]
                table.add_row(
                    "SQLite",
                    "[green]OK[/green]",
                    f"Users={users_count}, Audit events={events_count}",
                )
            except Exception as e:
                table.add_row(
                    "SQLite",
                    "[red]ERROR[/red]",
                    f"DB issue: {e}",
                )
        else:
            table.add_row(
                "SQLite",
                "[yellow]DISABLED[/yellow]",
                "USE_SQLITE is False; using in-memory USERS_DB and file logs only.",
            )

        console.print(table)

    def run(self):  # To start the command loop
        
        """
        The main application loop that handles user input and command dispatching.
        """
        
        self.clear()  # Clears the screen and shows the banner
        console.print("System online. Type [bold cyan]help[/bold cyan] for commands.")  # Prints a startup hint
        
        # Continuous loop until 'exit' command
        while True:
            try:
                # Repaint the UI banner each time
                # self.print_banner() -> REMOVED: Redundant, handled by clear()

                
                # Prompt the operator for the next command
                cmd = Prompt.ask("\n[blink bold cyan]MISSION_CONTROL>[/blink bold cyan] ").strip().lower()  # Prompts for a command and normalizes it
                
                # --- COMMAND DISPATCHER ---
                if cmd == "exit":  # Checks for the exit command
                    console.print("[bold green]\nConsole Session Terminated.[/bold green]\n")  # Prints termination message
                    break  # Breaks the loop to exit
                
                elif cmd == "help":  # Checks for the help command
                    self.help_menu()  # Displays the help menu
                    
                elif cmd == "status":  # Checks for the status command
                    self.print_status_panel()  # Displays the status panel
                    
                elif cmd == "login":  # Checks for the login command
                    self.login()  # Runs the login flow
                    
                elif cmd == "logout":  # Checks for the logout command
                    # Reset session variables
                    self.current_user = None  # Clears the current user
                    self.current_role = None  # Clears the current role
                    console.print("Logged out successfully.")  # Prints a logout message
                    
                elif cmd == "scan":  # Checks for the scan command
                    self.scan()  # Runs the scan flow
                    
                elif cmd == "ingest":  # Checks for the ingest command
                    self.ingest()  # Runs the ingest flow
                    
                elif cmd == "process":  # Checks for the process command
                    self.process()  # Runs the process flow
                    
                elif cmd == "archive":  # Checks for the archive command
                    self.archive()  # Runs the archive flow
                    
                elif cmd == "hack":  # Checks for the hack command
                    self.hack()  # Runs the hack flow
                    
                elif cmd == "recover":  # Checks for the recover command
                    self.recover()  # Runs the recovery flow
                    
                elif cmd == "rotate_keys":
                    self.rotate_keys()

                elif cmd == "ids":
                    self.run_ids()
                
                elif cmd == "bruteforce_login":
                    self.scenario_bruteforce_login()

                elif cmd == "tamper_metadata":
                    self.scenario_tamper_metadata()

                elif cmd == "delete_backup":
                    self.scenario_delete_backup()
                
                elif cmd == "full_attack":
                    self.scenario_full_attack()
                
                elif cmd == "add":
                    self.user_add()

                elif cmd == "list":
                    self.user_list()

                elif cmd == "remove":
                    self.user_remove()

                elif cmd == "change_role":
                    self.user_change_role()

                elif cmd == "disable":
                    self.user_disable()
                
                elif cmd == "health":
                    self.health()
                    
                elif cmd == "":  # Checks for empty input
                    pass  # Do nothing for empty input
                
                else:  # Else branch for unknown command
                    # Inform the user of invalid input
                    console.print(f"[red]Error: Unknown mission command '{cmd}'.[/red]")  # Prints unknown command error
                
                # Pause the screen so the operator can review the result
                input("\n[Press Enter to return to console]")
                self.clear()  # Clears the screen after the pause
                
            except KeyboardInterrupt:  # Starts KeyboardInterrupt handler
                console.print("\n[bold]Emergency Stop: Session Terminated.[/bold]")  # Prints termination message
                break  # Breaks the loop to exit on Ctrl+C
            except Exception as e:  # Starts generic exception handler
                 # Catch and report any unhandled crashes to keep the console alive
                console.print(f"[bold red]SYSTEM ERROR:[/bold red] {e}")  # Prints the error message



if __name__ == "__main__":
    
    # --- STARTUP ENVIRONMENT CLEANING ---
    if os.path.exists("simulation_data"):  # Checks for existing simulation data
        # Import shutil to delete old artifacts and start with a clean slate
        import shutil
        shutil.rmtree("simulation_data")  # Deletes the simulation data directory
        
    # --- LAUNCH APPLICATION ---
    session = InteractiveSession()  # Instantiates the session controller
    session.run()  # Starts the interactive loop
