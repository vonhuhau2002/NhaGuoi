"""Dựng Markdown và JSONL từ ghi chú đối chiếu; chạy offline, không nạp model.

Đây là bản ghi chú biên tập, không phải bản chép toàn văn bài báo/truyện gốc.
Chỉ số chunk theo tokenizer sẽ được xây ở giai đoạn triển khai tiếp theo.
"""

import hashlib
import json
from pathlib import Path
import unicodedata

BASE = Path(__file__).resolve().parents[2]
ROOT = BASE / "data/chatbot"


def main():
    sources = json.loads((ROOT / "manifests/sources.json").read_text())
    reviews = json.loads((ROOT / "manifests/source_reviews.json").read_text())
    downloads = {}
    for line in (ROOT / "manifests/downloads.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["status"] == "downloaded":
            downloads[row["source_id"]] = row
    output = ROOT / "clean"
    output.mkdir(exist_ok=True)
    records = []
    for source in sources:
        sid = source["source_id"]
        review = reviews[sid]
        if sid not in downloads:
            continue
        download = downloads[sid]
        if review.get("reviewed_raw_sha256") != download["sha256"]:
            raise ValueError(f"{sid}: raw mới chưa được đối chiếu lại với ghi chú")
        raw = BASE / download["raw_path"]
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == download["sha256"], sid
        lines = [f"# {sid} — {source['title']}", "",
                 f"- Nguồn: {source['url']}",
                 f"- Tác giả: {review['author'] or 'Chưa xác minh'}",
                 f"- Xuất bản: {review['published_at'] or 'Chưa xác minh'}",
                 f"- Raw: [{raw.name}](../raw/{raw.name})",
                 f"- SHA-256: `{download['sha256']}`",
                 f"- Đối chiếu: `{review['review_status']}`; sử dụng: `{review['usage']}`",
                 "", review['notes'], ""]
        if sid == "S01":
            text = unicodedata.normalize("NFC", raw.read_text(encoding="utf-8-sig"))
            lines += ["## Nội dung mẫu được cung cấp", "", text.strip(), ""]
        else:
            lines += ["Bản ghi chú tóm lược do trợ lý biên tập, chưa có người chuyên môn duyệt.",
                      "Không phải toàn văn nguyên tác. Vị trí đối chiếu trỏ về bản raw đã lưu.", ""]
        for block in review["blocks"]:
            text = unicodedata.normalize("NFC", block["text"])
            record = dict(document_id=f"{sid}:{block['id']}", source_id=sid,
                          title=source["title"], heading=block["heading"], text=text,
                          text_kind="editorial_summary", source_url=source["url"],
                          author=review["author"], published_at=review["published_at"],
                          retrieved_at=download["retrieved_at"], topics=source["topics"],
                          raw_path=download["raw_path"], raw_sha256=download["sha256"],
                          evidence_locator=block["locator"],
                          review_status=review["review_status"], usage=review["usage"],
                          production_approved=False)
            records.append(record)
            lines += [f"## {block['heading']}", "", f"ID: `{record['document_id']}`", "",
                      text, "", "Vị trí đối chiếu: " + json.dumps(block["locator"], ensure_ascii=False), ""]
        (output / f"{sid}.md").write_text("\n".join(lines), encoding="utf-8")
    (output / "documents.jsonl").write_text("".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    print(f"{len(downloads)} raw xác minh hash; {len(records)} ghi chú JSONL; chưa có vector index.")


if __name__ == "__main__":
    main()
