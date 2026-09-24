---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: false
---

{% include base_path %}

{% assign postsByYear = site.publications | group_by_exp: "post", "post.date | date: '%Y'" %}

{% for year in postsByYear reversed %}
  <div style="margin-top: 3em;">
    <h2 style="color: black; border-bottom: 2px solid black; font-weight: bold;">
      {{ year.name }}
    </h2>
    {% for post in year.items %}
      {% if post.teaser %}
        <div class="pub-with-teaser">
          <div class="pub-teaser-img">
            <a href="{{ base_path }}{{ post.url }}">
              <img src="{{ post.teaser | prepend: "/images/" | prepend: base_path }}" alt="{{ post.title }} - graphical abstract">
            </a>
          </div>
          <div class="pub-teaser-text">
            {% include archive-single.html %}
          </div>
        </div>
      {% else %}
        {% include archive-single.html %}
      {% endif %}
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

  /* Graphical-abstract / TOC image layout */
  .pub-with-teaser {
    display: flex;
    align-items: flex-start;
    gap: 1.5em;
    margin-bottom: 1em;
  }
  .pub-teaser-img {
    flex: 0 0 160px;
  }
  .pub-teaser-img img {
    width: 160px;
    height: 160px;
    object-fit: contain;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #fff;
  }
  .pub-teaser-text {
    flex: 1 1 auto;
    min-width: 0;
  }
  @media (max-width: 600px) {
    .pub-with-teaser {
      flex-direction: column;
    }
    .pub-teaser-img img {
      width: 120px;
      height: 120px;
    }
  }
</style>
