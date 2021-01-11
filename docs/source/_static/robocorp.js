(function (window) {
  var showBanner = false;

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
      banner.style.display = "block";
      showBanner = true;
      resizePadding();
    }
  }

  function bannerDismiss() {
    setCookie("bannerDismiss", "1", 7);
    var banner = document.getElementById("robocorpBanner");
    banner.style.display = "none";
    showBanner = false;
    resizePadding();
  }

  function resizePadding() {
    if (showBanner) {
      var banner = document.getElementById("robocorpBanner");
      var padding = banner.offsetHeight + "px";
    } else {
      var padding = "0px";
    }

    var sidebar = document.getElementsByClassName("wy-side-scroll")[0];
    var content = document.getElementsByClassName("wy-nav-content-wrap")[0];
    sidebar.style.paddingTop = padding;
    content.style.paddingTop = padding;
  }

  window.bannerDismiss = bannerDismiss;
  window.addEventListener("load", bannerShow);
  window.addEventListener("resize", resizePadding);
})(window);
