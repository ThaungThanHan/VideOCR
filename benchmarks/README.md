# Benchmarks

Store benchmark metadata only. Do not commit private videos or full private subtitle outputs.

Required fields for each result:

- date
- host
- command
- input duration
- crop
- language
- wall-clock seconds
- peak RSS MB
- average CPU percent
- peak CPU percent
- output bytes
- cue count
- exit code
- SRT validation result
- notes on Hermes responsiveness

The first deployment gate is a successful real Chinese-subtitle extraction on Capsule Corp. Two-job behavior must be measured before enabling concurrency greater than one.
