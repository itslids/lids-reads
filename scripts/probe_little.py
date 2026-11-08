# Temporary probe (Lindsey OK'd 2026-11-08): how do tags on the "Little Lids" lists show up in the Hardcover API?
import json, os, urllib.request
Q = """{ me {
  lists(where: {name: {_ilike: "Little Lids%"}}) { name list_books { id book_id reason book { title } } }
  taggings(order_by: {id: desc}, limit: 40) { taggable_type taggable_id book { title } tag { tag tag_category { category } } }
} }"""
tok = os.environ["HARDCOVER_TOKEN"].strip()
tok = tok if tok.lower().startswith("bearer ") else "Bearer " + tok
req = urllib.request.Request("https://api.hardcover.app/v1/graphql", data=json.dumps({"query": Q}).encode(),
    headers={"content-type": "application/json", "authorization": tok, "user-agent": "lids-reads"})
print(json.dumps(json.load(urllib.request.urlopen(req, timeout=30)), indent=1))
