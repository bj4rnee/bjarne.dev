<p align="center">
  <img width="200" src="https://bjarne.dev/static/favicon.svg">
</p>

<p align="center">
  <a href="https://bjarne.dev">
    <img src="https://img.shields.io/badge/bjarne.dev-ttf?style=flat&logo=devdotto&logoColor=white"/>
  </a>
  <br>
</p>

# https://bjarne.dev

This is the repository of my personal homepage [bjarne.dev](https://bjarne.dev).

## Updating Font Awesome

Font Awesome Free is self-hosted under `bjarne_dev/static/assets/fontawesome/`.
To move to a newer release:

1. Download `fontawesome-free-<version>-web.zip` from the Font Awesome GitHub releases.
2. Overwrite `css/all.min.css` and the whole `webfonts/` folder with the ones from the zip.

## Updating PhotoSwipe

The photo gallery lightbox uses [PhotoSwipe](https://photoswipe.com) (v5, MIT),
self-hosted under `bjarne_dev/static/assets/js/photoswipe/` with its stylesheet
at `bjarne_dev/static/assets/css/photoswipe.css`. Currently pinned to 5.4.4. To
bump the version, overwrite the three files from the pinned release:

```bash
V=5.4.4
cd bjarne_dev/static/assets
curl -fsSL https://unpkg.com/photoswipe@$V/dist/photoswipe.esm.js -o js/photoswipe/photoswipe.esm.js
curl -fsSL https://unpkg.com/photoswipe@$V/dist/photoswipe-lightbox.esm.js -o js/photoswipe/photoswipe-lightbox.esm.js
curl -fsSL https://unpkg.com/photoswipe@$V/dist/photoswipe.css -o css/photoswipe.css
```