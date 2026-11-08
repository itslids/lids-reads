# Temporary probe (Lindsey OK'd 2026-11-08): how do tags on the "Little Lids" lists show up in the Hardcover API?
import json, os, urllib.request, urllib.error
QS = {
 "lists": '{ me { lists(where: {name: {_ilike: "Little Lids%"}}) { name list_books { id book_id reason book { title } } } } }',
 "taggings": '{ me { taggings(order_by: {id: desc}, limit: 40) { taggable_type taggable_id book { title } tag { tag } } } }',
}
tok = os.environ.get("HARDCOVER_TOKEN", "").strip()
print("token present:", bool(tok))
tok = tok if tok.lower().startswith("bearer ") else "Bearer " + tok
for name, q in QS.items():
    req = urllib.request.Request("https://api.hardcover.app/v1/graphql", data=json.dumps({"query": q}).encode(),
        headers={"content-type": "application/json", "authorization": tok, "user-agent": "lids-reads"})
    print("==", name)
    try:
        print(json.dumps(json.load(urllib.request.urlopen(req, timeout=30)), indent=1))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read()[:500])
