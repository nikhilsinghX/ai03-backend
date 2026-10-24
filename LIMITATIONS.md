# Known limitations

- Session storage is in-memory, not persistent SQLite. Restarting the backend loses all sessions.
- Web Speech API support varies by browser and environment; this build is intended for Chrome on localhost. Typed answers remain available.
- No Whisper fallback, authentication, ATS integration, or automatic hiring decision is included.
- Mock mode is useful for integration tests, not real candidate scoring.
- Assessment quality and quote verification should be validated with synthetic test cases before any real-world pilot.
