#!/usr/bin/env python3
"""
Migration script: Registry PeopleTableV2 → ugsys-user-profiles-{env}

What it does:
  1. Scans PeopleTableV2 for all users
  2. Transforms schema to the user-profile-service format
  3. Writes to ugsys-user-profiles-{env} using pk=PROFILE#{id}/sk=PROFILE

Fields migrated (complement to identity-manager migration):
  Registry field         → Profile service field
  phone                  → phone
  dateOfBirth            → date_of_birth
  address.*              → address.{street,city,state,postalCode,country}
  emailVerified          → email_verified
  requirePasswordChange  → require_password_change
  firstName + lastName   → full_name (denormalized)
  email                  → email (denormalized)

NOTE: Run AFTER ugsys-user-profile-service is deployed to prod.
      Run AFTER identity-manager migration so user_ids are consistent.

Usage:
  # Dry run (default)
  uv run python scripts/migrate_from_registry.py

  # Live run
  uv run python scripts/migrate_from_registry.py --execute

  # Target environment
  uv run python scripts/migrate_from_registry.py --env prod --execute
"""

import argparse
import sys
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError


def scan_all(table: object) -> list[dict]:  # type: ignore[type-arg]
    """Full table scan with pagination."""
    items: list[dict] = []  # type: ignore[type-arg]
    kwargs: dict[str, Any] = {}
    while True:
        resp = table.scan(**kwargs)  # type: ignore[attr-defined]
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return items


def transform(person: dict) -> dict:  # type: ignore[type-arg]
    """Convert a Registry person item to user-profile-service item."""
    user_id = person["id"]
    now = datetime.now(UTC).isoformat()

    first = person.get("firstName", "").strip()
    last = person.get("lastName", "").strip()
    full_name = f"{first} {last}".strip() or "Unknown"

    addr = person.get("address") or {}

    created_at = person.get("createdAt", now)
    updated_at = person.get("updatedAt", now)

    return {
        "pk": f"PROFILE#{user_id}",
        "sk": "PROFILE",
        "user_id": user_id,
        "email": person.get("email", "").lower().strip(),
        "full_name": full_name,
        "phone": person.get("phone", ""),
        "date_of_birth": person.get("dateOfBirth", ""),
        "address": {
            "street": addr.get("street", ""),
            "city": addr.get("city", ""),
            "state": addr.get("state", ""),
            "postal_code": addr.get("postalCode", ""),
            "country": addr.get("country", ""),
        },
        "email_verified": person.get("emailVerified", False),
        "require_password_change": person.get("requirePasswordChange", False),
        "created_at": created_at,
        "updated_at": updated_at,
        "migrated_from": "registry",
        "migrated_at": now,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate user profiles from Registry to user-profile-service"
    )
    parser.add_argument("--env", default="prod", help="Target environment (default: prod)")
    parser.add_argument(
        "--source-table", default="PeopleTableV2", help="Registry people table"
    )
    parser.add_argument(
        "--target-table", default="", help="Override target table name"
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually write to DynamoDB (default: dry run)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip users already in target (default: True)",
    )
    args = parser.parse_args()

    target_table = args.target_table or f"ugsys-user-profiles-{args.env}"
    dry_run = not args.execute

    print("=" * 60)
    print("Registry → User Profile Service Migration")
    print("=" * 60)
    print(f"  Source table : {args.source_table}")
    print(f"  Target table : {target_table}")
    print(f"  Region       : {args.region}")
    print(f"  Mode         : {'DRY RUN' if dry_run else '⚠️  LIVE WRITE'}")
    print()

    dynamodb = boto3.resource("dynamodb", region_name=args.region)
    source = dynamodb.Table(args.source_table)
    target = dynamodb.Table(target_table)

    print("Scanning source table...")
    people = scan_all(source)
    print(f"Found {len(people)} users in {args.source_table}")
    print()

    existing_ids: set[str] = set()
    if args.skip_existing and not dry_run:
        print("Scanning target table for existing profiles...")
        existing = scan_all(target)
        existing_ids = {item.get("user_id", "") for item in existing}
        print(f"Found {len(existing_ids)} existing profiles — will skip them")
        print()

    migrated = skipped = errors = 0

    for person in people:
        user_id = person.get("id", "")
        email = person.get("email", "").lower().strip()

        if not user_id or not email:
            print(f"  [SKIP] Missing id or email: {person}")
            skipped += 1
            continue

        if user_id in existing_ids:
            print(f"  [SKIP] Already exists: {email}")
            skipped += 1
            continue

        item = transform(person)

        if dry_run:
            print(
                f"  [DRY RUN] Would migrate: {email} | "
                f"phone={item['phone'] or 'none'} | "
                f"city={item['address']['city'] or 'none'} | "
                f"email_verified={item['email_verified']}"
            )
            migrated += 1
        else:
            try:
                target.put_item(Item=item)
                print(f"  [OK] Migrated: {email}")
                migrated += 1
            except ClientError as e:
                print(f"  [ERROR] Failed to migrate {email}: {e}")
                errors += 1

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Migrated : {migrated}")
    print(f"  Skipped  : {skipped}")
    print(f"  Errors   : {errors}")
    if dry_run:
        print()
        print("This was a DRY RUN. Run with --execute to apply changes.")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
