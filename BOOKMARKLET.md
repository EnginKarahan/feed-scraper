# Feed Scraper Bookmarklet

## Installation

Ziehe den folgenden Link in deine Lesezeichen-Leiste:

**[Feed zu Feed Scraper hinzufügen](javascript:(function(){var%20url=encodeURIComponent(window.location.href);var%20name=encodeURIComponent(window.document.title.replace(/[^a-z0-9]/gi,'-').substring(0,50));window.open('http://192.168.178.103:5000/?add='+url+'&name='+name);})();)**

Oder erstelle manuell ein Lesezeichen mit diesem Code:

```javascript
javascript:(function(){
  var url = encodeURIComponent(window.location.href);
  var name = encodeURIComponent(window.document.title.replace(/[^a-z0-9]/gi, '-').substring(0,50));
  window.open('http://192.168.178.103:5000/?add=' + url + '&name=' + name);
})();
```

**WICHTIG:** Ersetze `192.168.178.103:5000` mit deiner tatsächlichen Server-Adresse.

## Verwendung

1. Besuche eine Webseite
2. Klicke auf das Lesezeichen
3. Der Feed Scraper öffnet sich mit der URL
4. Feed-Name anpassen und erstellen

## Für Tailscale-Nutzer

Wenn du Tailscale verwendest, ersetze die IP durch deine Tailscale-IP:

```javascript
javascript:(function(){
  var url = encodeURIComponent(window.location.href);
  var name = encodeURIComponent(window.document.title.replace(/[^a-z0-9]/gi, '-').substring(0,50));
  window.open('http://DEINE_TAILSCALE_IP:5000/?add=' + url + '&name=' + name);
})();
```
