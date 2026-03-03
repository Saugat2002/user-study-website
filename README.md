# Image Quality User Study

## How to run

**Requirements:** Python 3 (no extra packages needed — uses only the standard library)

```bash
python server.py
```

The browser will open automatically at `http://localhost:8080`.  
If it doesn't, open that URL manually.

## What happens

- Participants enter their name, then complete 3 pages of 10 samples each (30 total).
- Each row shows the same prompt rendered by 4 different AI methods in a **randomised column order** (so participants cannot identify methods by position).
- On the final page the participant clicks **Submit Study**.
- Results are saved to the `results/` folder as `{name}_{timestamp}.json`.

## Fallback (no server)

If the server is not running, participants can still open `index.html` directly in a browser (`File > Open`).  
Submission will offer a **Download Results JSON** button instead of automatic saving.

## Results format

```json
{
  "username": "Alice",
  "session_seed": 847263910,
  "timestamp": "2026-03-03T11:09:03.000Z",
  "summary": {
    "counts":      { "sd": 5, "ddpo": 7, "b2": 8, "ours": 10 },
    "percentages": { "sd": 16.7, "ddpo": 23.3, "b2": 26.7, "ours": 33.3 },
    "total": 30
  },
  "details": {
    "1": {
      "prompt": "A dog washing dishes",
      "preferred_method": "ours",
      "column_order": ["b2", "ours", "sd", "ddpo"]
    }
  }
}
```
