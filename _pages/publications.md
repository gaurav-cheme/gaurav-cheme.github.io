---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---

{% assign postsByYear = site.publications | group_by_exp: "post", "post.date | date: '%Y'" %}

{% for year in postsByYear reversed %}
  <div style="margin-top: 3em;">
    <h2 style="color: black; border-bottom: 2px solid black; font-weight: bold;">
      {{ year.name }}
    </h2>
    {% for post in year.items %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
{% endfor %}

<style>
  /* Force all publication text to black */
  .archive__item-title a { color: black !important; font-weight: bold; }
  .archive__item-excerpt { color: black !important; }
  .page__content { color: black !important; }
  
  /* Style the abstract toggle */
  details summary { 
    color: black; 
    cursor: pointer; 
    margin-bottom: 10px;
    font-weight: 500;
  }
</style>
