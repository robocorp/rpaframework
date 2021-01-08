(function (window) {
  function setCookie(name, value, days) {
    var expires = "";
    if (days) {
      var date = new Date();
      date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
      expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
  }

  function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(";");
    for (var i = 0; i < ca.length; i++) {
      var c = ca[i];
      while (c.charAt(0) == " ") {
        c = c.substring(1, c.length);
      }
      if (c.indexOf(nameEQ) == 0) {
        return c.substring(nameEQ.length, c.length);
      }
    }
    return null;
  }

  function show(elem, display) {
    var el = document.getElementById(elem);
    el.style.display = display || "block";
    el.style.opacity = 1;
  }

  function hide(elem) {
    var el = document.getElementById(elem);
    el.style.opacity = 1;
    el.style.display = "none";
  }

  function cookieConsent() {
    if (!getCookie("cookieDismiss")) {
      show("cookieConsentContainer");
    }
  }

  function cookieDismiss() {
    setCookie("cookieDismiss", "1", 7);
    hide("cookieConsentContainer");
  }

  window.cookieDismiss = cookieDismiss;
  window.addEventListener("load", cookieConsent);
})(window)
