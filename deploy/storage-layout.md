# Storage Layout

Use a dedicated non-root extraction user and keep job data outside the repository.

Suggested root:

```text
/var/lib/subextractor/
  uploads/
  work/
  results/
  jobs/
    <job-id>/
      input.mp4
      output.srt
      progress.jsonl
      cancel
```

The engine should only read the job input and write inside the job directory or an explicitly configured allowed root.
