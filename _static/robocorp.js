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

  function bannerShow() {
    if (!getCookie("bannerDismiss")) {
      var el = document.getElementById("robocorpBanner");
      el.style.display = "block";
      var el = document.getElementsByClassName("wy-side-scroll")[0];
      el.style.marginTop = "50px";
    }
  }

  function bannerDismiss() {
    setCookie("bannerDismiss", "1", 7);
    var el = document.getElementById("robocorpBanner");
    el.style.display = "none";
    var el = document.getElementsByClassName("wy-side-scroll")[0];
    el.style.marginTop = "0px";
  }

  window.bannerDismiss = bannerDismiss;
  window.addEventListener("load", bannerShow);
})(window)
