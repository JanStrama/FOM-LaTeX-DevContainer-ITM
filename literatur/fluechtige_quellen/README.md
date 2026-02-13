# Fluechtige Quellen

Dieses Verzeichnis dient zur Ablage fluechtiger Quellen und KI-Chat-Exporte.

## Struktur

- `ki_chats/`: PDF- oder Markdown-Exporte von KI-Chatverlaeufen
- `convert_session.py`: Konvertiert JSON/JSONL-Chat-Exporte nach Markdown (optional PDF)

## Beispiel

```bash
python3 literatur/fluechtige_quellen/convert_session.py \
  --input export.jsonl \
  --output literatur/fluechtige_quellen/ki_chats \
  --to-pdf
```

