# Manual server validation checklist

Not executed by the unit suite. Use a test server and back up its world and plugin data. Confirm Endstone 0.11.14, the exact BDS build/platform, and the server process working directory. The supplied geometry evidence applies to Linux x86-64 BDS 1.26.52.3.

1. Install the built wheel and start with `tick-distance=4`. Check the English enable log and the effective value. Verify `/phantom` is registered and player help/status is Chinese.
2. With a previously unseen UUID, confirm on is the default. Run `/phantom off`, check the saved acknowledgment, reconnect, restart the server, and confirm it remains off. If practical, verify an account rename with the same UUID preserves the setting.
3. With only disabled players covering a target chunk, verify a phantom spawn event at that chunk is cancelled. Verify another mob still spawns. The public event cannot select natural-only sources, so command/egg checks only establish their own event path.
4. For D=4, place an enabled neighbor at chunk offset `(4,1)` relative to the target and verify the plugin stops restricting that chunk. Move them to `(4,2)` and verify restriction resumes. Repeat signed/axis-swapped boundaries and positions just below zero. For odd D, restart with D=5 and check `(5,1)` versus `(5,2)`.
5. Move the enabled neighbor into another dimension, disconnect them, and teleport them back. Query status immediately after each change. Check enabled-player names and that there is no stale movement cache. Native callback ordering may need observation at a tick boundary.
6. Verify status and the spawn result agree at the querying player's current chunk. Verify an uncovered chunk remains untouched. A query reports this plugin's restriction, not the complete runtime world's spawn probability or global gamerule value.
7. In a controlled nighttime/insomnia setup with the requisite vanilla conditions, compare natural spawns with on/off. Record global `doinsomnia`, difficulty, player conditions, chunk readiness and observation duration. An absence of phantoms alone is not proof that cancellation ran.
8. Confirm existing phantoms remain, can cross boundaries and may attack. Confirm events cancelled by another test plugin remain cancelled here.
9. Check console `phantom status`, `phantom on` and `phantom off` give English help without storing any console identity. Deny `antiphantom.command` to a test player and confirm all mutations and status requests are refused.
10. On disposable copies only, test missing/invalid `server.properties`, malformed preference JSON and an unwritable preference directory. Verify explicit startup/save errors, unchanged original data, and no false success acknowledgment. Restore valid files before restarting.

Record exact versions, wheel hash, settings and observed outcomes. Do not label this checklist passed merely because synthetic tests or package imports passed.
