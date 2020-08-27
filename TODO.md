- [ ] Split up !yt, !ytdl & !spotify for more granular control of which commands
to disable in case of missing API credentials.

    -  No spotify creds: Disable !spotify
    -  No YouTube creds: Disable !yt
    - !ytdl should remain enabled regardless

- [ ] Move config.py to top-level directory and add as bot attribute