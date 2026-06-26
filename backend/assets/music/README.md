# Background Music Library

Drop royalty-free `.mp3` or `.wav` files into the matching mood folder below.
The app automatically picks a random track from the right folder based on
the detected mood of each generated script. If a folder is empty, that
video simply renders without background music (voiceover still works
fine) — so the app never breaks, it just sounds better once you add files.

```
assets/music/
  upbeat/
  calm/
  cinematic/
  dramatic/
  funny/
  corporate/
  lofi/
```

## Where to get free, legal tracks (no API key needed)

- **YouTube Audio Library** – studio.youtube.com → Audio Library. Free for
  any use, including monetized videos. Filter by mood/genre, download mp3.
- **Pixabay Music** – pixabay.com/music. Royalty-free, no attribution
  required for most tracks (check each license).
- **Free Music Archive** – freemusicarchive.org. Filter by CC license.
- **Incompetech (Kevin MacLeod)** – incompetech.com. Royalty-free with
  attribution (credit "Kevin MacLeod, incompetech.com" in your video
  description).

Aim for 5-10 tracks per mood folder, each 1-3 minutes long — the renderer
automatically loops/trims tracks to match the final video length.
