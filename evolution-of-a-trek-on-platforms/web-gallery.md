---
description: Since May 2021
---

# Web Gallery

<figure><img src="https://ysqlt77jtllpkzuoskytbkqovjouubb34uuqmi6igo7wwzrx3toa.arweave.net/xKC5_-ma1vVmjpKxMKoOql1KBDvlKQYjyDO_a2Y33Nw" alt=""><figcaption><p><strong>awalkaday 42-2022</strong></p></figcaption></figure>

Once the art project resumed in the [spring of 2021](https://github.com/awalkaday/about-awalkaday-art/commit/32eced8e914f46d9364a5d5fb6ec11c5bd7be7a4), a limited number of the salvaged photos began to be steadily uploaded to a purpose-built web gallery, [`awalkaday.art`](https://awalkaday.art/), which ultimately hosts a catalog of 263 photographs from the collection in a custom-designed, interactive and responsive gallery.

{% embed url="https://awalkaday.art" %}
Make a short trip to the online gallery and encounter in a random order the photos
{% endembed %}

<figure><img src="../.gitbook/assets/web-gallery-overview.PNG" alt="Screenshot of the web gallery: awalkaday.art" width="563"><figcaption><p>A screenshot of the custom-built web gallery</p></figcaption></figure>

The web gallery prioritizes a smooth and random order of display for each visit, allowing for ease of navigation and discovery of photographs by surprising visitors with fresh-eye perspectives every load time. The gallery's code enforcing mathematical randomness in JavaScript dates from [February 2023](https://github.com/awalkaday/awalkaday-art/commits/master/assets/js/main.js).

{% embed url="https://github.com/awalkaday/awalkaday-art/commit/3043b3f1e58f05bfdefd7bdf9afcf9fddcf9ea96" %}

{% code title="awalkaday-art/tree/master/assets/js/main.js‎" %}
```js
			// Main.
			var $main = $('#main');

			// Thumbs.
			$main.children('.thumb').each(function() {
			var $this = $(this),
				$image = $this.find('.image'),
				$image_img = $image.children('img'),
				randomPos;

			// Set random background position.
			randomPos = Math.floor(Math.random() * 100);
			$image.css('background-position', `${randomPos}%`);

			// Shuffle the elements.
			$main.children('.thumb').sort(function() {
			return Math.random() - 0.5;
			}).appendTo($main);
```
{% endcode %}

A 3D exhibition hall, constructed since the springtime of 2023, welcomes all digital visitors at [oncyber.io/awalkaday.art](https://oncyber.io/awalkaday.art). The virtual exhibition, which caught the attention of silicon-based reality promoters at launch in the spring of 2024, remains open to this day.

{% embed url="https://oncyber.io/awalkaday.art" %}
Enter the virtual exhibition space inside an environment that simulates a lifelike display of 24 photographs
{% endembed %}

{% embed url="https://www.instagram.com/walk.day/reel/C4lci5_r0a8/" %}
A web browser-based tour of the virtual exhibition hall dedicated to `awalkaday.art`
{% endembed %}

<p align="center"></p>

<p align="center"><strong><code>14</code></strong></p>
