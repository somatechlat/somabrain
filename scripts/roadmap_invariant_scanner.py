#!/usr/bin/env python3
"""
Roadmap Invariant Scanner - Phase 0 Strict-Mode Enforcement

This scanner ensures AROMADP strict-mode compliance by detecting:
- Banned keywords (fakeredis, sqlite://, etc.)
- JSON fallback paths
- Disabled feature flags
- Non-Avro serialization
- Incomplete mathematical implementations

Run as: python3 scripts/roadmap_invariant_scanner.py
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# AROMADP Strict-Mode Violations to detect
BANNED_KEYWORDS = [
    "fakeredis",
    "sqlite://",
    "noop tracer",
    "disable_auth",
    "KafkaProducer",  # kafka-python legacy
    "json.loads",  # JSON serialization instead of Avro
    "json.dumps",  # JSON serialization instead of Avro
]

    # Required patterns for mathematical correctness
REQUIRED_PATTERNS = {
        "fusion_normalization": r"e_norm.*=.*\(error.*-.*mu.*\)/\(sigma.*\+.*epsilon\)",
        "consistency_kappa": r"kappa.*=.*1.*-.*JSD",
        "tau_annealing": r"tau.*=.*tau.*\*.*gamma.*\^.*t",
        "brier_score": r"brier.*=.*\(prediction.*-.*actual\)\s*\*\s*\2",
        "ece_calculation": r"ECE.*=.*Σ.*\|.*confidence.*-.*accuracy.*\|",
    }class RoadmapInvariantScanner:
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.violations: List[Tuple[str, int, str, str]] = []
        
    def scan_python_files(self) -> List[Tuple[str, int, str, str]]:
        """Scan Python files for banned keywords and missing patterns."""
        python_files = list(self.root_path.rglob("*.py"))
        
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Check for banned keywords
                    self._check_banned_keywords(file_path, lines)
                    
                    # Check for required mathematical patterns
                    self._check_required_patterns(file_path, content)
                    
                    # Check AST for specific patterns
                    self._check_ast_patterns(file_path, content)
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return self.violations
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Skip test files and generated files."""
        skip_patterns = [
            'test_',
            '__pycache__',
            '.git',
            'venv',
            '.venv',
            'node_modules',
            'dist',
            'build',
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _check_banned_keywords(self, file_path: Path, lines: List[str]) -> None:
        """Check for banned keywords in each line."""
        for lineno, line in enumerate(lines, 1):
            line = line.strip()
            for keyword in BANNED_KEYWORDS:
                if keyword.lower() in line.lower():
                    # Check if it's actually used (not in comment/string)
                    if self._is_actual_usage(line, keyword):
                        self.violations.append((
                            str(file_path),
                            lineno,
                            f"BANNED_KEYWORD: {keyword}",
                            line
                        ))
    
    def _is_actual_usage(self, line: str, keyword: str) -> bool:
        """Determine if the keyword is actually used, not just mentioned."""
        # Skip comments and strings
        line = re.sub(r'#.*$', '', line)
        line = re.sub(r'"[^"]*"', '""', line)
        line = re.sub(r"'[^']*'", "''", line)
        
        return keyword.lower() in line.lower()
    
    def _check_required_patterns(self, file_path: Path, content: str) -> None:
        """Check for required mathematical patterns."""
        for pattern_name, pattern in REQUIRED_PATTERNS.items():
            if not re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                self.violations.append((
                    str(file_path),
                    0,
                    f"MISSING_PATTERN: {pattern_name}",
                    f"Expected pattern: {pattern}"
                ))
    
    def _check_ast_patterns(self, file_path: Path, content: str) -> None:
        """Use AST to check for specific patterns."""
        try:
            tree = ast.parse(content)
            
            # Check for KafkaProducer usage (legacy)
            class KafkaVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.has_kafka_producer = False
                    
                def visit_Call(self, node):
                    if isinstance(node.func, ast.Name) and node.func.id == 'KafkaProducer':
                        self.has_kafka_producer = True
                    self.generic_visit(node)
            
            visitor = KafkaVisitor()
            visitor.visit(tree)
            
            if visitor.has_kafka_producer:
                self.violations.append((
                    str(file_path),
                    0,
                    "LEGACY_KAFKA",
                    "Found KafkaProducer from kafka-python instead of confluent-kafka"
                ))
                
        except SyntaxError:
            pass  # Skip files with syntax errors
    
    def scan_configuration_files(self) -> List[Tuple[str, int, str, str]]:
        """Scan configuration files for disabled features."""
        config_files = [
            'data/feature_overrides.json',
            'config/*.yaml',
            'config/*.yml',
        ]
        
        for pattern in config_files:
            for config_file in self.root_path.rglob(pattern):
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                        
                    # Check for disabled roadmap features
                    if 'fusion_normalization"' in content and '"disabled"' in content:
                        self.violations.append((
                            str(config_file),
                            0,
                            "DISABLED_FEATURE",
                            "fusion_normalization disabled in configuration"
                        ))
                    
                except (FileNotFoundError, PermissionError):
                    continue
                    
        return self.violations
    
    def generate_report(self) -> str:
        """Generate a comprehensive report of violations."""
        if not self.violations:
            return "✅ All roadmap invariants satisfied - AROMADP strict-mode compliance achieved!"
        
        report = [
            "🔍 Roadmap Invariant Scanner Report",
            "=" * 50,
            "",
            "❌ Violations Found:",
            ""
        ]
        
        for file_path, lineno, violation_type, detail in self.violations:
            report.append(f"📍 {file_path}:{lineno}")
            report.append(f"   🔴 {violation_type}")
            report.append(f"   📄 {detail}")
            report.append("")
        
        report.extend([
            "🔧 Fix these violations to achieve full roadmap compliance:",
            "1. Remove banned keywords",
            "2. Enable disabled features",
            "3. Ensure mathematical formulas are implemented",
            "4. Use confluent-kafka only",
            ""
        ])
        
        return "\n".join(report)


def main():
    """Main execution function."""
    scanner = RoadmapInvariantScanner()
    
    print("🔍 Scanning for roadmap invariants...")
    
    # Scan Python files
    violations = scanner.scan_python_files()
    
    # Scan configuration files
    violations.extend(scanner.scan_configuration_files())
    
    # Generate and print report
    report = scanner.generate_report()
    print(report)
    
    # Exit with appropriate code
    if violations:
        print(f"\n❌ Found {len(violations)} violations")
        sys.exit(1)
    else:
        print("\n✅ Roadmap compliance achieved!")
        sys.exit(0)


if __name__ == "__main__":
    main()