# M666 — Symmetric Interaction Matrix

M666 defines the 666 canonical slots for 36 genes: 630 unordered pairs plus 36 diagonal self-relations. It stores active relations sparsely; it does not pre-create 666 records.

The matrix is symmetric: (i,j) and (j,i) resolve to one slot. Relation weights and confidence must be evidence-backed.

## Run
```bash
python -m pip install -r requirements.txt
python -m pip install -e .
pytest -q
```

See `M666_SPEC.md` for the standard.
