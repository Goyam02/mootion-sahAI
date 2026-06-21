# Curriculum Roadmap Shape

This is the contract we are locking in for Mootion curriculum data.

## Shape

```json
{
  "version": "1.0",
  "title": "Electricity and Circuits",
  "subject": "Physics",
  "grade": "8",
  "source_type": "manual",
  "source_text": null,
  "source_subject": null,
  "document_id": null,
  "root": {
    "id": "root",
    "title": "Electricity and Circuits",
    "kind": "module",
    "order": 0,
    "metadata": {},
    "children": [
      {
        "id": "unit_1",
        "title": "Electric Current",
        "kind": "unit",
        "order": 0,
        "metadata": {},
        "children": [
          {
            "id": "topic_1",
            "title": "Current and Voltage",
            "kind": "topic",
            "order": 0,
            "metadata": {},
            "children": []
          }
        ]
      }
    ]
  },
  "nodes": [
    {
      "id": "root",
      "title": "Electricity and Circuits",
      "kind": "module",
      "order": 0,
      "metadata": {}
    }
  ],
  "edges": [
    {
      "id": "root-unit_1",
      "source": "root",
      "target": "unit_1",
      "kind": "contains"
    }
  ]
}
```

## Notes

- `root` is the canonical curriculum tree.
- `nodes` and `edges` are the flattened graph form we can feed to a future roadmap UI or AI generator.
- `kind` should stay limited to `module`, `unit`, `topic`, `subtopic`, or `lesson`.
- `source_type` is manual for now, but the same structure will later support `syllabus`, `document`, `subject`, and `ncert`.
- The AI generator later should only fill this shape, not invent a new one.
