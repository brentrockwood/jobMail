#!/usr/bin/env python3
"""
JobMail - AI-powered Gmail inbox classifier for job application emails.

This is the main entry point for the application. It provides a CLI interface
for processing emails, viewing statistics, and managing the classification system.
"""

import argparse
import logging
import sys
from pathlib import Path

from src.classifier import create_classifier
from src.config import Config, setup_logging
from src.gmail_client import GmailClient
from src.processor import EmailProcessor
from src.storage import EmailStorage

logger = logging.getLogger(__name__)


def cmd_run(args: argparse.Namespace, config: Config) -> int:
    """
    Run email processing.

    Args:
        args: Parsed command line arguments
        config: Application configuration

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        logger.info("Initializing JobMail processor...")
        logger.info(f"AI Provider: {config.ai_provider}")
        logger.info(f"Confidence Threshold: {config.confidence_threshold}")
        logger.info(f"Batch Size: {config.batch_size}")
        logger.info(f"Dry Run: {config.dry_run}")

        if config.dry_run:
            logger.warning("DRY RUN MODE: No changes will be made to Gmail")

        # Initialize processor (creates components internally)
        processor = EmailProcessor(config)

        # Build Gmail query
        query = args.query or "in:inbox"
        if args.after:
            query += f" after:{args.after}"
        if args.before:
            query += f" before:{args.before}"

        logger.info(f"Gmail Query: {query}")

        # Process inbox
        logger.info(f"Gmail Query: {query}")

        # Process inbox
        logger.info("Starting email processing...")
        stats = processor.process_inbox(query=query, max_messages=args.limit)

        # Report results
        logger.info("\n" + "=" * 60)
        logger.info("PROCESSING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Emails found: {stats['found']}")
        logger.info(f"Emails processed: {stats['processed']}")
        logger.info(f"Emails skipped (already processed): {stats['skipped']}")
        logger.info("=" * 60)

        # Show database statistics
        db_stats = processor.get_stats()
        if db_stats:
            logger.info("\nDATABASE STATISTICS:")
            logger.info("-" * 60)
            for category, count in sorted(db_stats.items()):
                logger.info(f"  {category:20s}: {count:5d}")
            logger.info("-" * 60)
            logger.info(f"  {'TOTAL':20s}: {sum(db_stats.values()):5d}")
            logger.info("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.info("\nProcessing interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        return 1


def cmd_stats(args: argparse.Namespace, config: Config) -> int:
    """
    Display statistics from the database.

    Args:
        args: Parsed command line arguments
        config: Application configuration

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        storage = EmailStorage(config.database_path)
        stats = storage.get_stats()

        if not stats:
            print("No processed emails in database yet.")
            return 0

        print("\n" + "=" * 60)
        print("JOBMAIL STATISTICS")
        print("=" * 60)
        print(f"Database: {config.database_path}")
        print("-" * 60)

        for category, count in sorted(stats.items()):
            print(f"  {category:20s}: {count:5d}")

        print("-" * 60)
        print(f"  {'TOTAL':20s}: {sum(stats.values()):5d}")
        print("=" * 60)

        # Show recent emails if requested
        if args.recent:
            print(f"\nRECENT PROCESSED EMAILS (last {args.recent}):")
            print("-" * 60)
            recent = storage.get_recent_processed(limit=args.recent)
            for email in recent:
                print(f"\n  {email['processed_at']}")
                print(f"  From: {email['from_email']}")
                print(f"  Subject: {email['subject'][:70]}...")
                print(f"  Classification: {email['classification']} (confidence: {email['confidence']:.2f})")
                print(f"  Provider: {email['provider']} / {email['model']}")
                if email['label_applied']:
                    print(f"  Label: {email['label_applied']}", end="")
                    if email['archived']:
                        print(" + ARCHIVED")
                    else:
                        print()

        return 0

    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}", exc_info=True)
        return 1


def cmd_reset(args: argparse.Namespace, config: Config) -> int:
    """
    Reset the database (clear all processed email records).

    Args:
        args: Parsed command line arguments
        config: Application configuration

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        storage = EmailStorage(config.database_path)
        stats = storage.get_stats()
        total = sum(stats.values()) if stats else 0

        if not args.force:
            print(f"This will delete {total} processed email records from the database.")
            print(f"Database: {config.database_path}")
            response = input("Are you sure? (yes/no): ")
            if response.lower() != "yes":
                print("Reset cancelled.")
                return 0

        storage.clear_all()
        logger.info(f"Database reset: deleted {total} records")
        print(f"✓ Database reset successfully ({total} records deleted)")
        return 0

    except Exception as e:
        logger.error(f"Error resetting database: {e}", exc_info=True)
        return 1


def main() -> int:
    """
    Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="JobMail - AI-powered Gmail inbox classifier for job application emails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: from config/env)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Process emails from Gmail inbox",
    )
    run_parser.add_argument(
        "--query",
        help="Gmail search query (default: 'in:inbox')",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of emails to process (default: from config BATCH_SIZE)",
    )
    run_parser.add_argument(
        "--after",
        help="Process emails after this date (YYYY/MM/DD format)",
    )
    run_parser.add_argument(
        "--before",
        help="Process emails before this date (YYYY/MM/DD format)",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't make any changes to Gmail (log only)",
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Display statistics from the database",
    )
    stats_parser.add_argument(
        "--recent",
        type=int,
        metavar="N",
        help="Also show N most recently processed emails",
    )

    # Reset command
    reset_parser = subparsers.add_parser(
        "reset",
        help="Reset database (clear all processed email records)",
    )
    reset_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    # Show help if no command provided
    if not args.command:
        parser.print_help()
        return 1

    try:
        # Load configuration
        config = Config.from_env()

        # Override config with CLI arguments
        if args.log_level:
            config.log_level = args.log_level  # type: ignore

        if hasattr(args, "dry_run") and args.dry_run:
            config.dry_run = True

        if hasattr(args, "limit") and args.limit:
            config.batch_size = args.limit

        # Setup logging
        setup_logging(config.log_level)

        # Validate configuration
        config.validate()

        # Route to appropriate command
        if args.command == "run":
            return cmd_run(args, config)
        elif args.command == "stats":
            return cmd_stats(args, config)
        elif args.command == "reset":
            return cmd_reset(args, config)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        # If logging isn't set up yet, print to stderr
        if not logging.getLogger().handlers:
            print(f"ERROR: {e}", file=sys.stderr)
        else:
            logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
