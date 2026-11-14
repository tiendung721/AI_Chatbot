import argparse
import getpass
import json
import os
import secrets
from pathlib import Path
from typing import Any

from .auth import passwords
from .common import canonical, new_id
from .config import settings
from .content import audit, create_text, publish_snapshot
from .db import one, run, transaction
from .schemas import AssistantConfig, KnowledgeText


def provision_tenant(slug: str, name: str) -> tuple[str, str]:
    with transaction(privileged=True) as db:
        existing = one(db, "SELECT id FROM tenants WHERE slug=:slug", slug=slug)
        if existing:
            a = one(db, "SELECT public_key FROM assistants WHERE tenant_id=:t", t=existing["id"])
            assert a
            return str(existing["id"]), a["public_key"]
        tenant_id, assistant_id = new_id(), new_id()
        public_key = slug + "-" + secrets.token_hex(6)
        config = AssistantConfig(name="Trợ lý " + name).model_dump(mode="json")
        run(
            db,
            "INSERT INTO tenants(id,slug,display_name) VALUES(:id,:slug,:name)",
            id=tenant_id,
            slug=slug,
            name=name,
        )
        run(
            db,
            "INSERT INTO assistants(id,tenant_id,public_key) VALUES(:id,:t,:key)",
            id=assistant_id,
            t=tenant_id,
            key=public_key,
        )
        run(
            db,
            "INSERT INTO assistant_drafts(tenant_id,assistant_id,config_json) VALUES(:t,:a,CAST(:config AS jsonb))",
            t=tenant_id,
            a=assistant_id,
            config=canonical(config),
        )
    return tenant_id, public_key


def provision_admin(tenant_id: str, email: str, password: str, *, rotate: bool = False) -> str:
    with transaction(tenant_id, privileged=True) as db:
        # Serialize provisioning so the one-active-admin constraint also holds during handover.
        run(db, "SELECT id FROM tenants WHERE id=:t FOR UPDATE", t=tenant_id)
        current = one(
            db, "SELECT account_id FROM tenant_admin_memberships WHERE tenant_id=:t AND active", t=tenant_id
        )
        if current and not rotate:
            raise ValueError("Phường đã có Admin hoạt động. Dùng rotate-admin để bàn giao.")
        if current:
            run(
                db,
                "UPDATE tenant_admin_memberships SET active=false WHERE tenant_id=:t AND active",
                t=tenant_id,
            )
            run(db, "UPDATE accounts SET active=false WHERE id=:id", id=current["account_id"])
            run(
                db,
                "UPDATE admin_sessions SET revoked_at=now() WHERE account_id=:id",
                id=current["account_id"],
            )
        account_id = new_id()
        run(
            db,
            "INSERT INTO accounts(id,tenant_id,email,password_hash) VALUES(:id,:t,:email,:pw)",
            id=account_id,
            t=tenant_id,
            email=email.lower(),
            pw=passwords.hash(password),
        )
        run(
            db,
            "INSERT INTO tenant_admin_memberships(id,tenant_id,account_id) VALUES(:id,:t,:a)",
            id=new_id(),
            t=tenant_id,
            a=account_id,
        )
        audit(
            db, tenant_id, account_id, "ops.admin_rotated" if rotate else "ops.admin_provisioned", account_id
        )
    return account_id


def seed_demo(credentials_path: Path, prefix: str = "ward-demo") -> None:
    if settings().app_env not in {"local", "test"}:
        raise RuntimeError("Demo seed chỉ được phép ở local/test.")
    credentials: dict[str, Any] = (
        json.loads(credentials_path.read_text(encoding="utf-8"))
        if credentials_path.exists() and prefix == "ward-demo"
        else {}
    )
    for letter in ("a", "b"):
        slug = f"{prefix}-{letter}"
        tenant_id, public_key = provision_tenant(slug, f"PHƯỜNG MẪU {letter.upper()} — DỮ LIỆU KIỂM THỬ")
        email = f"admin-{letter}@example.invalid" if prefix == "ward-demo" else f"{slug}@example.invalid"
        with transaction(tenant_id, privileged=True) as db:
            existing = one(
                db,
                "SELECT account_id FROM tenant_admin_memberships WHERE tenant_id=:t AND active",
                t=tenant_id,
            )
        if existing:
            # Never reset an existing password or content on a repeated bootstrap.
            credentials.setdefault(
                slug,
                {
                    "email": email,
                    "public_key": public_key,
                    "note": "Tài khoản đã tồn tại; mật khẩu không được thay đổi.",
                },
            )
            continue
        password = secrets.token_urlsafe(22)
        account_id = provision_admin(tenant_id, email, password)
        with transaction(tenant_id, privileged=True) as db:
            marker = "LAM-A-482" if letter == "a" else "TIM-B-937"
            body = f"DỮ LIỆU KIỂM THỬ, KHÔNG PHẢI HƯỚNG DẪN HÀNH CHÍNH THẬT.\n\nThủ tục minh họa của phường mẫu {letter.upper()}: chuẩn bị phiếu thử nghiệm và mã màu {marker}. "
            if letter == "b":
                body += "Mật mã thử nghiệm riêng của phường B là BONG-SEN-B-915."
            doc = create_text(
                db, tenant_id, account_id, KnowledgeText(title="Thủ tục minh họa — dữ liệu giả", body=body)
            )
            run(
                db, "UPDATE document_versions SET approved_for_public=true WHERE id=:id", id=doc["version_id"]
            )
            config = AssistantConfig(
                name=f"Trợ lý phường mẫu {letter.upper()}",
                knowledge_version_ids=[doc["version_id"]],
                conversation_starters=["Thủ tục minh họa cần chuẩn bị gì?"],
            ).model_dump(mode="json")
            run(
                db,
                "UPDATE assistant_drafts SET config_json=CAST(:config AS jsonb) WHERE tenant_id=:t",
                config=canonical(config),
                t=tenant_id,
            )
            publish_snapshot(
                db, tenant_id, account_id, config, "Dữ liệu mẫu local, không dùng cho production"
            )
        credentials[slug] = {"email": email, "password": password, "public_key": public_key}
    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    credentials_path.write_text(json.dumps(credentials, ensure_ascii=False, indent=2), encoding="utf-8")
    if os.name != "nt":
        credentials_path.chmod(0o600)
    print(
        "Đã kiểm tra/khởi tạo hai phường mẫu. Thông tin đăng nhập nằm trong file local được bỏ qua bởi Git."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Developer-only operations; never expose over HTTP")
    parser.add_argument("namespace", choices=["ops"])
    parser.add_argument(
        "command",
        choices=[
            "seed-demo",
            "prepare-e2e",
            "create-tenant",
            "provision-admin",
            "rotate-admin",
            "validate-runtime",
            "init-storage",
            "create-embedding-profile",
            "reindex-knowledge",
            "sweep-orphans",
        ],
    )
    parser.add_argument("--slug")
    parser.add_argument("--name")
    parser.add_argument("--tenant")
    parser.add_argument("--email")
    parser.add_argument("--apply", action="store_true", help="Apply orphan cleanup; default is dry-run")
    parser.add_argument("--grace-hours", type=int, default=24)
    parser.add_argument("--maximum", type=int, default=1000)
    parser.add_argument("--credentials-path", default="/app/.local/provisioned-admins.json")
    args = parser.parse_args()
    if args.command == "seed-demo":
        seed_demo(Path(args.credentials_path))
    elif args.command == "prepare-e2e":
        if Path(args.credentials_path).name == "provisioned-admins.json":
            parser.error("prepare-e2e cần --credentials-path riêng, không ghi đè tài khoản local")
        seed_demo(Path(args.credentials_path), prefix="e2e-" + secrets.token_hex(5))
    elif args.command == "create-tenant":
        if not args.slug or not args.name:
            parser.error("--slug và --name là bắt buộc")
        _, public_key = provision_tenant(args.slug, args.name)
        print("Đã tạo tenant. Assistant public key:", public_key)
    elif args.command in {"provision-admin", "rotate-admin"}:
        if not args.tenant or not args.email:
            parser.error("--tenant và --email là bắt buộc")
        password = getpass.getpass("Mật khẩu cấp lần đầu (ít nhất 14 ký tự): ")
        if len(password) < 14:
            parser.error("Mật khẩu phải có ít nhất 14 ký tự")
        with transaction(privileged=True) as db:
            tenant = one(db, "SELECT id FROM tenants WHERE slug=:slug", slug=args.tenant)
        if not tenant:
            parser.error("Tenant không tồn tại")
        provision_admin(str(tenant["id"]), args.email, password, rotate=args.command == "rotate-admin")
        print("Đã cấp Admin và thu hồi phiên cũ nếu có bàn giao.")
    elif args.command == "validate-runtime":
        from .main import check_runtime

        check_runtime()
        print("Runtime configuration and database isolation checks passed.")
    elif args.command == "init-storage":
        from .storage import initialize_storage

        initialize_storage()
        print("Private object storage initialized.")
    elif args.command == "create-embedding-profile":
        from .ai.embeddings import create_profile

        create_profile()
        print("Embedding profile checked/created. No provider request was made.")
    elif args.command == "sweep-orphans":
        from .ingestion.cleanup import sweep_orphans

        if not args.tenant:
            parser.error("--tenant slug is required; cleanup never scans all tenants")
        with transaction(privileged=True) as db:
            tenant = one(db, "SELECT id FROM tenants WHERE slug=:slug", slug=args.tenant)
        if not tenant:
            parser.error("Tenant does not exist")
        print(
            canonical(
                sweep_orphans(
                    str(tenant["id"]), apply=args.apply, grace_hours=args.grace_hours, maximum=args.maximum
                )
            )
        )
    elif args.command == "reindex-knowledge":
        from .ai.embeddings import reindex

        if not args.tenant:
            parser.error(
                "--tenant slug is required; approved knowledge may be sent to the configured provider"
            )
        with transaction(privileged=True) as db:
            tenant = one(db, "SELECT id FROM tenants WHERE slug=:slug", slug=args.tenant)
        if not tenant:
            parser.error("Tenant does not exist")
        print("Indexed chunks:", reindex(str(tenant["id"])))


if __name__ == "__main__":
    main()
