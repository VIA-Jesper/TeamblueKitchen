# Teamblue Kitchen Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

En Home Assistant integration til at vise menuen fra Teamblue kantinen, samt indhold i fryseren.

## Funktioner

- **Dagens Ret**: Viser hvad der er til frokost i dag.
- **Ugeplan**: Gemmer ugeplanen lokalt, så du kan se hele ugen selvom API'et kun viser fremadrettet.
- **Fryser**: Viser antal og liste over retter, der kan købes i fryseren.

## Installation

### Via HACS (Anbefalet)

1. Sørg for at [HACS](https://hacs.xyz/) er installeret.
2. Gå til HACS -> Integrations.
3. Klik på menuen (tre prikker) øverst til højre -> "Custom repositories".
4. Tilføj URL'en til dette repository og vælg kategorien **Integration**.
5. Klik **Install**.
6. Genstart Home Assistant.

### Manuel Installation

1. Download `teambluekitchen` mappen.
2. Kopier den til `custom_components/teambluekitchen` i din Home Assistant config mappe.
3. Genstart Home Assistant.

## Konfiguration

1. Gå til **Indstillinger** -> **Enheder og tjenester**.
2. Klik **Tilføj integration**.
3. Søg efter **Teamblue Kitchen**.
4. Bekræft eller ret API URL'en.

## Sensorer

Integrationen opretter følgende sensorer:

*   `sensor.teamblue_todays_meal` (Dagens Ret)
*   `sensor.teamblue_week_plan` (Ugeplan - se attributter for detaljer)
*   `sensor.teamblue_freezer_count` (Antal retter i fryseren)

## Dashboard Eksempler

Integrationen leverer data i attributterne, som kan vises på mange måder. Her er nogle eksempler til din Lovelace konfiguration.

### Simpel Ugeplan (Markdown Kort)
Dette kort viser hele ugeplanen pænt listet op.

```yaml
type: markdown
title: 🍽️ Ugeplan
content: |
  {% set days = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag'] %}
  {% for day in days %}
    {% set dish = state_attr('sensor.teamblue_week_plan', day) %}
    {% if dish %}
  **{{day}}**
  {{ dish }}
  
  ---
    {% endif %}
  {% endfor %}
```

### Dagens Ret med Billede (Picture Entity)
Da sensoren automatisk genererer et billede af retten, kan du bruge et helt simpelt billed-kort.

```yaml
type: picture-entity
entity: sensor.teamblue_todays_meal
name: Dagens Ret
show_state: true
show_name: true
```

### Avanceret "Menu Kort"
Hvis du vil have det til at ligne en rigtig restaurant-menu (kræver at du installerer `Mushroom Cards` fra HACS).

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-title-card
    title: "Kantinen"
    subtitle: "Dagens ret og ugeplan"
  - type: custom:mushroom-template-card
    primary: "{{ states('sensor.teamblue_todays_meal') }}"
    secondary: "Dagens Ret"
    icon: mdi:food-turkey
    icon_color: orange
    picture: "{{ state_attr('sensor.teamblue_todays_meal', 'entity_picture') }}"
    layout: vertical
```

## Automatiseringer

Her er nogle idéer til, hvordan du kan bruge integrationen i automatiseringer.

### Besked om morgenen
Få en notifikation hver morgen kl. 07:00 med dagens ret, så du ved om du skal glæde dig til frokost.

```yaml
alias: "Kantine: Dagens ret"
description: "Sender en besked med dagens ret hver morgen"
trigger:
  - platform: time
    at: "07:00:00"
condition:
  - condition: time
    weekday:
      - mon
      - tue
      - wed
      - thu
      - fri
action:
  - service: notify.mobile_app_din_telefon
    data:
      title: "🍴 Dagens Ret"
      message: "{{ states('sensor.teamblue_todays_meal') }}"
      data:
        image: "{{ state_attr('sensor.teamblue_todays_meal', 'entity_picture') }}"

### Alarm: Livretter på menuen
Få besked, når menuen opdateres (f.eks. fredag), hvis din livret er på menuen i den kommende uge.

```yaml
alias: "Kantine: Livretter Alarm"
description: "Giver besked hvis der er Lasagne eller Kødsovs på menuen"
trigger:
  - platform: state
    entity_id: sensor.teamblue_week_plan
condition:
  - condition: template
    value_template: >
      {# Ret dine livretter herunder, adskilt af | #}
      {% set favorites = 'Lasagne|Kødsovs|Boller i karry' %}
      {% set dishes = state_attr('sensor.teamblue_week_plan', 'dishes') %}
      
      {# Tjekker om en af retterne matcher #}
      {{ dishes | select('search', favorites, ignorecase=True) | list | length > 0 }}
action:
  - service: notify.mobile_app_din_telefon
    data:
      title: "🚨 LIVRET ALARM!"
      message: "Der er en af dine favoritter på menuen i næste uge! Tjek ugeplanen."
      data:
        url: "/lovelace/kantine" # Link til dit dashboard
```

## FAQ / Tips

**Hvordan tvinger jeg en opdatering?**
Da integrationen kun henter data hver 24. time, kan du tvinge en ny hentning ved at gå til:
*Indstillinger -> Enheder og tjenester -> Teamblue Kitchen -> Klik på de tre prikker -> "Genindlæs"*

**Hvorfor ser maden mærkelig ud på billedet?**
Billederne genereres ("tegnes") af en kunstig intelligens (AI) baseret på rettens navn. Den gør sit bedste, men nogle gange kan danske retter se lidt fantasifulde ud. Det er en del af charmen! 🤖🎨

**Data mangler?**
Hvis API'et ikke har frigivet næste uges menu endnu, vil ugeplanen være tom eller vise den nuværende uge indtil opdateringen sker.
```
