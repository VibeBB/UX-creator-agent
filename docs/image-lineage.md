# Auxiliary image ancestry and review scope

Original renderer and liaison-response images retain their resolved path,
SHA-256 and owning plugin. Auxiliary crops, tiles and composites explicitly
reference those original revisions. Filenames and directory exclusions do
not establish ownership or ancestry.

Pass optional `image_details` to `ux_render`, or to `ux_liaison_status` with
`attach_images: true`:

```json
{
  "dir": "out/kettle",
  "image_details": [
    {
      "path": "out/kettle/detail.png",
      "parents": ["out/kettle/kettle.statechart.png"],
      "operation": "crop"
    }
  ]
}
```

The detail must already exist. Its parents must be intact originals in that
same tool response; copied paths, self-reference, duplicate parents, paths
outside the workspace and changed revisions are rejected. `crop` and `tile`
have one parent; `composite` accepts up to sixteen unique original parents.
This is declared auxiliary ancestry, not proof of the pixel transformation.
Do not declare formal product outputs as auxiliary views.

Inline receipts preserve the exact auxiliary bytes, original parent hashes,
owners and native receiving session. The Stop hook consumes only intact
receipt identities. Each plugin owes reviews for its own original subjects;
auxiliary views do not multiply product obligations. Unknown ownership keeps
the conservative legacy obligation. Invalid ancestry is an explicit gap.
A changed original requires a review of its current hash. Reviews of a tile
alone cannot satisfy an original's review requirement.

Review checkpoint creation normalizes receipted auxiliary images to their
intact originals and deduplicates source/checklist pairs. A conflicting
checklist or changed/ambiguous parent fails closed. All existing bounded
primary/blind collection and reconciliation rules still apply.

Delivery, ownership and ancestry are advisory evidence. They do not prove
model perception, deterministic gate success, workflow completion or product
acceptance. Historical four-field original identities remain compatible.
