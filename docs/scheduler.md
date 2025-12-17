## Weekly refresh (local)

### macOS launchd (runs every Monday at 8am)

1. Save a plist at `~/Library/LaunchAgents/com.ent.refresh.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.ent.refresh</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>bash</string>
    <string>-lc</string>
    <string>cd /Users/Maria/Documents/ent_research && source .venv/bin/activate && python cli/refresh.py refresh && osascript -e 'display notification "ENT refresh done" with title "ENT Research Tool"'</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>8</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>/Users/Maria/Documents/ent_research/logs/ent_refresh.out</string>
  <key>StandardErrorPath</key><string>/Users/Maria/Documents/ent_research/logs/ent_refresh.err</string>
</dict>
</plist>
```

2. Load it: `launchctl load ~/Library/LaunchAgents/com.ent.refresh.plist`

3. Check: `launchctl list | grep com.ent.refresh`

### Cron (alternative)

Edit crontab: `crontab -e` and add:

```
0 8 * * 1 cd /Users/Maria/Documents/ent_research && source .venv/bin/activate && python cli/refresh.py refresh && osascript -e 'display notification "ENT refresh done" with title "ENT Research Tool"'
```

This runs Mondays at 8am and shows a local notification.
