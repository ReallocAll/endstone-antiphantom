# Design and evidence

## Coverage contract

Convert block-space positions to chunk coordinates using `floor(x / 16)` and `floor(z / 16)`, including negative coordinates. For a candidate chunk offset `(dx, dz)` from a player's current center, the supplied BDS 1.26.52.3 investigation gives:

```text
max(abs(dx), abs(dz)) <= D
and abs(dx) + abs(dz) <= D + 1
```

`D` is the effective `server.properties` tick-distance, clamped to 4..12. This is a clipped diamond rather than a square or a simple Manhattan-radius-D diamond. Counts for D=4..12 are **57, 81, 109, 141, 177, 217, 261, 309, 361**.

For each event/status query, the implementation reads each online player's current location and preference. It uses level name plus dimension name as the public identity key; dimension type alone would conflate custom dimensions. Covered players form a union; any enabled player wins. With covered players but no enabled player, the plugin blocks. With no covered players, it abstains.

A shared pure `decide` function handles both event and status decisions. Names are included only for the query explanation and are never persistent identity. No per-chunk materialization, range enumeration, periodic actor scans, or movement/dimension caches are needed. A relevant event or query is O(online players); non-phantom and already-cancelled events return before scanning. A toggle writes the preference file synchronously and then reports current status.

## Evidence boundaries

### User-supplied binary investigation

The binary was identified by the user as **Linux x86-64 BDS 1.26.52.3**. Their supplied analysis links configuration to offset generation at `0xCA33510`, center selection at `0x74CE800`, and the chunk-tick path at `0xC9E2940`, followed by entity-tick qualification. It reports that a new player center is used on the next system call and same-dimension candidate areas combine by union.

This plugin implements the reported candidate formula and reads current positions at decision time. The binary investigation was **not independently reproduced here**. The plugin does not inspect internal BDS candidate sets, chunk readiness or entity-tick gates. Endstone callback timing and live server behavior still require integration validation. A candidate footprint is not proof of simulation eligibility for every entity or of a natural phantom spawn.

### Public Endstone source

Reviewed tag **v0.11.14**, resolved commit `03f4189b1535af0870861748fc569f6deac0ad65`:

- [Public Player/Server API](https://github.com/EndstoneMC/endstone/blob/03f4189b1535af0870861748fc569f6deac0ad65/endstone/__init__.pyi): online players and `Player.unique_id`.
- [Level/Dimension/Location API](https://github.com/EndstoneMC/endstone/blob/03f4189b1535af0870861748fc569f6deac0ad65/endstone/level/__init__.pyi): location and dimension names; no public gamerule getter.
- [Event registration](https://github.com/EndstoneMC/endstone/blob/03f4189b1535af0870861748fc569f6deac0ad65/endstone/plugin/__init__.py): concrete event-class annotation required. The listener module deliberately does not use postponed/string annotations.
- [ActorSpawnEvent contract](https://github.com/EndstoneMC/endstone/blob/03f4189b1535af0870861748fc569f6deac0ad65/include/endstone/event/actor/actor_spawn_event.h): cancellation, with spawn cause still absent.
- [Runtime event hook](https://github.com/EndstoneMC/endstone/blob/03f4189b1535af0870861748fc569f6deac0ad65/src/endstone/runtime/bedrock_hooks/script_level_gameplay_handler.cpp): receives an already-added actor, emits the event, and cancellation flags/removes/despawns it. This is not a pre-allocation natural-spawn veto.
- [Linux launcher](https://github.com/EndstoneMC/endstone/blob/03f4189b1535af0870861748fc569f6deac0ad65/endstone/cli/linux.py) and [Windows launcher](https://github.com/EndstoneMC/endstone/blob/03f4189b1535af0870861748fc569f6deac0ad65/endstone/cli/windows.py): BDS process working directory is the server directory.

The callback only ever changes cancellation from false to true. It never clears another plugin's cancellation. This does not prevent another independently installed plugin from subsequently clearing this plugin's cancellation.

## Initialization and persistence

Native host-backed properties are not accessed in the Python constructor. On enable, both the server setting and the full preference document must validate before the listener is registered. Failure explicitly disables the plugin and leaves commands/event handlers guarded. Unknown UUIDs use vanilla-friendly default on.

The entire input is validated before publishing loaded state. A save prepares a new dictionary, serializes it into a same-directory temporary file, flushes and syncs that file, replaces the destination, and then publishes in-memory state. There is no shutdown-only save and no success acknowledgment before the replacement. Corrupt inputs remain available for operator recovery. No names, XUIDs or authentication data are stored.

## Tests and remaining checks

The geometry oracle uses independently enumerated row widths and fixed totals rather than calling the production predicate to generate expected data. Signed/swapped boundaries discriminate a square, simple diamond, off-by-one radius and truncation-toward-zero errors. Tests cover all D=4..12, overlap/order independence, dimension separation, live-position reads, no-coverage abstention, status/event parity, pre-cancelled/non-phantom events, permission/console behavior, UUID rename/restart, invalid inputs and injected file failures.

Installed-wheel checks load the actual `endstone` entry point and instantiate public SDK metadata. Host, player and event behavior tests use explicit synthetic objects; they do not claim actual networked clients or BDS event delivery. Run the separate server checklist on the target server before relying on live behavior.
