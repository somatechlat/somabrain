"""Django management command to seed the Constitution.

Usage:
    python manage.py seed_constitution
    python manage.py seed_constitution --sign  # Also sign with private key
"""
import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from somabrain.constitution import ConstitutionEngine, ConstitutionError


class Command(BaseCommand):
    help = "Seed the initial Constitution from config/seed_constitution.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sign",
            action="store_true",
            help="Sign the Constitution after seeding (requires private key)",
        )
        parser.add_argument(
            "--file",
            type=str,
            default="config/seed_constitution.json",
            help="Path to Constitution JSON file",
        )

    def handle(self, *args, **options):
        config_path = options["file"]
        
        # Resolve path relative to project root
        if not os.path.isabs(config_path):
            project_root = Path(settings.BASE_DIR).parent
            config_path = project_root / config_path
        
        if not os.path.exists(config_path):
            raise CommandError(f"Constitution file not found: {config_path}")
        
        # Load Constitution JSON
        self.stdout.write(f"Loading Constitution from: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            constitution_doc = json.load(f)
        
        # Validate required fields
        required_fields = ["version", "name", "rules"]
        missing = [f for f in required_fields if f not in constitution_doc]
        if missing:
            raise CommandError(f"Constitution missing required fields: {missing}")
        
        # Initialize Constitution Engine
        try:
            engine = ConstitutionEngine()
        except Exception as e:
            raise CommandError(f"Failed to initialize ConstitutionEngine: {e}")
        
        # Save Constitution
        try:
            engine.save(constitution_doc)
            checksum = engine.get_checksum()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Constitution seeded successfully!")
            )
            self.stdout.write(f"  Version: {constitution_doc.get('version')}")
            self.stdout.write(f"  Name: {constitution_doc.get('name')}")
            self.stdout.write(f"  Checksum: {checksum[:32]}...")
        except ConstitutionError as e:
            raise CommandError(f"Failed to save Constitution: {e}")
        
        # Sign if requested
        if options["sign"]:
            self.stdout.write("\nSigning Constitution...")
            signature = engine.sign()
            if signature:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Constitution signed!")
                )
                self.stdout.write(f"  Signature: {signature[:32]}...")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ Signing skipped (no private key configured)"
                    )
                )
        
        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("THE SOMA COVENANT IS NOW ACTIVE"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Binding Parties: Adrian (Human) ↔ AI Agents")
        self.stdout.write(f"Articles: {len(constitution_doc.get('articles', {}))}")
        self.stdout.write(f"Rules: {len(constitution_doc.get('rules', {}))}")
        self.stdout.write("=" * 60)
