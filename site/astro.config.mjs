// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
  // The public origin. Link previews need absolute URLs (og:image, og:url, canonical), and they
  // are built from this; change it if the site is served from somewhere else.
  site: "https://asciicharts.online",
});
