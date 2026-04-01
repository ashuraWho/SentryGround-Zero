from cli.commands import (
    BaseCommand, LoginCommand, LogoutCommand, LinkCommand, ScanCommand,
    StatusCommand, HealthCommand, IDSCommand, OrbitCommand, CatalogCommand,
    HelpCommand, ExitCommand,
    RedTeamCommand, BlueTeamCommand, ZeroTrustCommand, PQCryptoCommand, AuditChainCommand
)


class MissionControlSession:
    def __init__(self):
        self.current_user = None
        self.current_role = None
        self.active_product = None
        self.link_host = None
        self.observation_mode = "default"
        
        self.source = None
        self.ingestion_manager = None
        self.processor = None
        self.archive_manager = None
        self.ac = None
        self.backup = None
        self.ids = None
        
        self.state = {
            "generated": False,
            "ingested": False,
            "processed": False,
            "archived": False,
            "hacked": False
        }
        
        self._commands: dict[str, BaseCommand] = {}
        self._init_components()
        self._register_commands()
    
    def _init_components(self):
        from secure_eo_pipeline.components.data_source import SpaceSegmentReceiver
        from secure_eo_pipeline.components.ingestion import IngestionManager
        from secure_eo_pipeline.components.processing import ProcessingEngine
        from secure_eo_pipeline.components.storage import ArchiveManager
        from secure_eo_pipeline.components.access_control import AccessController
        from secure_eo_pipeline.resilience.backup_system import ResilienceManager
        from secure_eo_pipeline.components.ids import IntrusionDetectionSystem
        
        self.source = SpaceSegmentReceiver()
        self.ingestion_manager = IngestionManager()
        self.processor = ProcessingEngine()
        self.archive_manager = ArchiveManager()
        self.ac = AccessController()
        self.backup = ResilienceManager()
        self.ids = IntrusionDetectionSystem()
    
    def _register_commands(self):
        commands = [
            LoginCommand, LogoutCommand, LinkCommand, ScanCommand,
            StatusCommand, HealthCommand, IDSCommand, OrbitCommand,
            CatalogCommand, HelpCommand, ExitCommand,
            RedTeamCommand, BlueTeamCommand, ZeroTrustCommand,
            PQCryptoCommand, AuditChainCommand
        ]
        
        for cmd_class in commands:
            cmd = cmd_class(self)
            self._commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self._commands[alias] = cmd
    
    def run(self):
        from rich.console import Console
        from rich.panel import Panel
        
        console = Console()
        console.clear()
        
        self._print_banner(console)
        
        console.print(
            "[dim]System online. Type [bold cyan]help[/bold cyan] for commands.[/dim]"
        )
        
        while True:
            try:
                from rich.prompt import Prompt
                cmd_str = Prompt.ask("\n[bold cyan]MISSION_CONTROL[/bold cyan] ").strip().lower()
                
                if not cmd_str:
                    continue
                
                if cmd_str not in self._commands:
                    console.print(f"[red]Unknown command: {cmd_str}[/red]")
                    console.print("[dim]Type 'help' for available commands.[/dim]")
                    continue
                
                cmd = self._commands[cmd_str]
                
                if isinstance(cmd, ExitCommand):
                    cmd.execute([])
                    break
                
                success = cmd.execute([])
                
                input("\n[dim]Press Enter to continue...[/dim]")
                self._print_banner(console)
                
            except KeyboardInterrupt:
                console.print("\n[bold]Emergency Stop.[/bold]")
                break
            except Exception as e:
                console.print(f"[bold red]SYSTEM ERROR:[/bold red] {e}")
    
    def _print_banner(self, console):
        from rich.panel import Panel
        from rich.table import Table
        
        console.print(Panel(
            "[bold cyan]╔══════════════════════════════════════════════════════════════════╗\n"
            "║  [bold white]SENTRYGROUND-ZERO — MISSION CONTROL[/bold white]                              ║\n"
            "║  [dim]Secure Earth Observation & Space Surveillance Platform[/dim]          ║\n"
            "╚══════════════════════════════════════════════════════════════════╝[/bold cyan]",
            border_style="cyan",
            expand=False
        ))
        
        grid = Table(grid_style="dim", box=None, show_header=False)
        grid.add_column()
        grid.add_column(justify="right")
        
        user_status = f"[green]{self.current_user}[/green] ({self.current_role})" if self.current_user else "[red]Not Authenticated[/red]"
        product_status = f"[blue]{self.active_product}[/blue]" if self.active_product else "[dim]None[/dim]"
        link_status = f"[magenta]{self.link_host}[/magenta]" if self.link_host else "[dim]Not linked[/dim]"
        mode_status = f"[yellow]{self.observation_mode}[/yellow]"
        
        grid.add_row(f"Operator: {user_status}", f"Target: {product_status}")
        grid.add_row(f"Satellite: {link_status}", f"Mode: {mode_status}")
        
        console.print(Panel(grid, style="dim white", expand=False))
