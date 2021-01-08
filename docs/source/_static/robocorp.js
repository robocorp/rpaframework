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
      var banner = document.getElementById("robocorpBanner");
      var sidebar = document.getElementsByClassName("wy-side-scroll")[0];
      var content = document.getElementsByClassName("wy-nav-content-wrap")[0];
      banner.style.display = "block";
      sidebar.style.paddingTop = "50px";
      content.style.paddingTop = "50px";
    }
  }

  function bannerDismiss() {
    setCookie("bannerDismiss", "1", 7);
    var banner = document.getElementById("robocorpBanner");
    var sidebar = document.getElementsByClassName("wy-side-scroll")[0];
    var content = document.getElementsByClassName("wy-nav-content-wrap")[0];
    banner.style.display = "none";
    sidebar.style.paddingTop = "0px";
    content.style.paddingTop = "0px";
  }

  window.bannerDismiss = bannerDismiss;
  window.addEventListener("load", bannerShow);
})(window)
