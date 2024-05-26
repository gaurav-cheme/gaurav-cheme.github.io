---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---

{% if scholar.google.com/citations?user=MdAFTWoAAAAJ&hl=en %}
  <div class="wordwrap">You can also find my articles on <a href="{{scholar.google.com/citations?user=MdAFTWoAAAAJ&hl=en}}">my Google Scholar profile</a>.</div>
{% endif %}

{% include base_path %}

{% for post in site.publications reversed %}
  {% include archive-single.html %}
{% endfor %}
