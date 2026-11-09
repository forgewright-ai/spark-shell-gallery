# spark-shell gallery

Themes and wallpapers for [spark-shell](https://github.com/forgewright-ai/spark-shell),
made by the people who use it and reviewed before they ship.

    spark-shell theme gallery          what the gallery offers now
    spark-shell theme install NAME     one put in place and used

`theme install` takes the gallery's newest release that a key in spark-shell's
`allowed-signers` signed: the key that signs spark-shell's own releases. It checks every
file of the theme or wallpaper against `index.tsv` in that release, its size and its
sha256, and holds the data to the format below before it keeps anything. It never takes a
release older than one it has seen. A theme lands with your saved themes
(`spark-shell theme NAME` brings it back); a wallpaper lands in
`~/.local/share/spark-shell/gallery`.

The gallery is data alone. No SVG, GIF, font or script, no link, nothing executable, and
nothing a theme names ever runs.

## A theme

A folder `themes/NAME` with two files and at most one picture:

- `look.env`: `FORMAT=2` first, then any of the keys a shared theme may set, each one
  value of its list. A key left out keeps what the person has.

  | Key                | Values                                                         |
  | ------------------ | -------------------------------------------------------------- |
  | `PALETTE`          | where the colors came from: a word, such as `words` or `picture` |
  | `WORDS`            | the words that made it: letters, digits, spaces, `, . -`; 80 at most |
  | `WALLPAPER`        | `default` (the ground), `picture`, `#rrggbb`, or a drawing spark-shell ships (`fjord`, `meadow`...) |
  | `PICTURE`          | the picture's file name in the folder, when `WALLPAPER=picture` |
  | `FACE`             | `neon`, `argon`, `xenon`, `radon` or `krypton`                 |
  | `GLYPH_FAMILY`     | `stone`, `star` or `banner`                                    |
  | `ANIMATION`        | `none`, `moon`, `ripple`, `tide`, `embers`, `sun` or `flight`  |
  | `ALPHA`            | how solid the windows are, `0.5` to `1`                        |
  | `BAR_GLYPHS`       | `signs` or `words`                                             |
  | `WALLPAPER_MOTION` | `on` or `off`                                                  |
  | `DIALOG_ICONS`     | `on` or `off`                                                  |
  | `DIALOG_SPACING`   | `none`, `groups` or `rows`                                     |

  A shared theme never sets the text size, the pointer or a path on anyone's machine.
- `palette.env`: the twenty colors, `THEME_BG`, `THEME_FG`, `THEME_ACCENT`, `THEME_MUTED`
  and `THEME_ANSI_0` to `THEME_ANSI_15`, each `#rrggbb` once. The text reads at 4.5 to 1
  on the ground at least, the accent at 3 to 1.
- A picture, when `look.env` says `WALLPAPER=picture`.

## A wallpaper

One picture, `wallpapers/NAME.png`, `NAME.jpg` or `NAME.jpeg`.

A name is lowercase letters, digits and `-`, 40 at most, used once across themes and
wallpapers, and none of spark-shell's own: its palettes, drawings and the words of
`spark-shell theme`.

## Pictures

A PNG or a JPEG, as its name says; 4 MiB at most and 7680x4320 at most; a still
picture's own parts alone. A photo can carry where and when it was taken, so metadata
(EXIF, XMP, text, C2PA), animation, private chunks and anything after the picture's end
are refused: `exiftool -all= FILE` or `mogrify -strip FILE` removes them. A PNG is saved
plain, not interlaced. It is your own work, or work you may share under this repository's
license.

## Adding one

1. Make the look in spark-shell: `spark-shell theme "WORDS"`, `spark-shell theme picture
   PATH`, or by hand, and keep it with `spark-shell theme save NAME`.
2. Copy `~/.config/spark-shell/themes/NAME/look.env` and `palette.env` into
   `themes/NAME/`, and the picture when its wallpaper is one. In `look.env`, remove the
   lines a shared theme never sets (`TEXT_SIZE`, `POINTER`, `DRAWING`).
3. `python3 tools/check.py --write` checks it and writes `index.tsv`.
4. Open a pull request with the theme and `index.tsv`, and one picture of it in use.

## Review and releases

Every pull request needs a green check and the owner's approval (`CODEOWNERS`). The check
is main's `tools/check.py` run on the pull request's tree, so nothing of a pull request
judges itself, and a contribution changes `themes/`, `wallpapers/` and `index.tsv` alone.
On request, a Claude Code session reviews it against [REVIEW.md](REVIEW.md) and hands its
review to the owner; it advises, and the owner decides. A release is a tag, `gallery-v1`,
`gallery-v2` and on, whose message opens with `spark-shell-gallery gallery-vN`, signed
with spark-shell's release key and made by the owner alone; `theme install` reads nothing
else, and a spark-shell release is never taken for one.

## License

MIT, as spark-shell. By opening a pull request you confirm the theme or the picture is
your own work, or that you have the right to share it under this license.
