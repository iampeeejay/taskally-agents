"""Trusted Medicals Social Agent — CLI & API"""
import json, sys
from pathlib import Path
from agent import (
    generate_post, save_draft, list_drafts, 
    approve_post, generate_batch_report
)

DRAFTS_DIR = Path(__file__).parent / "drafts"

def cmd_generate():
    """Generate 1 week of content (42 posts: 7 days × 2 times × 3 platforms)."""
    print("⏳ Generating 1 week of content...")
    posts = generate_batch_report()
    print(f"✅ Generated {len(posts)} posts")
    print(f"📁 Saved to: {DRAFTS_DIR}/")

def cmd_list(status="draft"):
    """List drafts by status."""
    drafts = list_drafts(status)
    if not drafts:
        print(f"No {status} posts found.")
        return
    print(f"\n📋 {status.upper()} Posts ({len(drafts)}):")
    print("=" * 70)
    for i, post in enumerate(drafts, 1):
        print(f"\n  #{i} | {post['platform']:15s} | {post['scheduled_date']} {post['scheduled_time']}")
        print(f"      📌 {post['headline'][:60]}")
        print(f"      📝 {post['caption'][:80]}...")

def cmd_preview(n: int = 1):
    """Preview a specific draft by number."""
    drafts = list_drafts("draft")
    if not drafts or n > len(drafts):
        print(f"No draft #{n}")
        return
    post = drafts[n-1]
    print(f"\n{'='*60}")
    print(f"  📍 {post['platform']}  |  {post['scheduled_date']} @ {post['scheduled_time']}")
    print(f"{'='*60}")
    print(f"\n  Headline: {post['headline']}")
    print(f"\n  Caption:\n  {post['caption']}")
    print(f"\n  Hashtags: {' '.join(post.get('hashtags', []))}")
    print(f"\n  Image prompt: {post['image_prompt'][:100]}...")
    print(f"\n  CTA: {post.get('calls_to_action', 'N/A')}")
    print(f"\n  Status: {post['status']}")
    print(f"{'='*60}")

def cmd_approve(n: int):
    """Approve a draft by number."""
    drafts = list_drafts("draft")
    if not drafts or n > len(drafts):
        print(f"No draft #{n}")
        return
    post = drafts[n-1]
    filename = post.get("_filename", "")
    if not filename:
        # Find by matching content
        for f in DRAFTS_DIR.glob("*.json"):
            if json.load(open(f)).get("headline") == post["headline"]:
                filename = f.name
                break
    approved = approve_post(filename)
    print(f"✅ Approved: {approved['platform']} — \"{approved['headline'][:50]}\"")

def cmd_report():
    """Show summary of all content in the pipeline."""
    drafts = list_drafts("draft")
    approved = list_drafts("approved")
    total = len(list(drafts for _ in [1]) or DRAFTS_DIR.glob("*.json"))
    
    print(f"\n📊 Content Pipeline Report")
    print(f"{'='*40}")
    print(f"  📝 Drafts:      {len(drafts)}")
    print(f"  ✅ Approved:    {len(approved)}")
    print(f"{'='*40}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cli.py <command> [args]")
        print("  generate    — Generate 1 week of content")
        print("  list        — List pending drafts")
        print("  preview N   — Preview draft #N")
        print("  approve N   — Approve draft #N")
        print("  report      — Show pipeline status")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "generate":
        cmd_generate()
    elif cmd == "list":
        cmd_list()
    elif cmd == "preview":
        cmd_preview(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    elif cmd == "approve":
        cmd_approve(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    elif cmd == "report":
        cmd_report()
    else:
        print(f"Unknown command: {cmd}")